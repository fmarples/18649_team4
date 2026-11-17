"""Back up and wipe all three Lab 5 Raft histories, then cold-start with the Pi leading.

    <zephyr-venv>/python lab5/pristine.py          # shows the plan, asks for WIPE
    <zephyr-venv>/python lab5/pristine.py --yes

Checkoff step 1 needs every node to boot in term 1 with the Pi as leader. The
firmware does that only on an empty store, and an empty Nucleo that cannot hear
the Pi elects a leader within about 100 ms. So this holds both Nucleos halted
under reset, erases flash sectors 6-7 only, clears the Pi store, starts the Pi
service, waits until it leads term 1, and only then releases the Nucleos.

Nothing is erased until all three backups are on this laptop and verified. If
any step fails, the Pi service is restarted and the Nucleos released, so the
cluster re-forms from whichever histories remain. Backups and `pristine.log`
go to `logs/lab5/pristine/<time>/`; the Pi keeps a second copy in
`~/.local/state/team4-lab5/pristine-backup-<time>/`.

Needs pyOCD with the STM32F401RE pack (the Zephyr venv has both), both
ST-LINKs on USB and the `wheelpi` SSH alias. Wheels can move on reset.
"""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from lab3_demo.pi_ssh import SSH, call, sudo, sudo_password  # noqa: E402

LOG = logging.getLogger('pristine')
PROBES = {'124020': 'n2', '171333': 'n3'}  # ST-LINK serial ending -> node
TARGET = 'stm32f401retx'
STATE_START, STATE_SIZE = 0x08040000, 0x40000  # sectors 6-7; firmware is sectors 0-5
FLASH_KIB_REGISTER, FLASH_KIB = 0x1FFF7A22, 512  # F401RE; a smaller part has no sector 7
DBGMCU_APB1_FZ, IWDG_STOP = 0xE0042008, 1 << 12
UNIT = 'team4-lab5-cockpit.service'
PI_STATE = '.local/state/team4-lab5'
PI_FILES = 'raft.bin display.sqlite display.sqlite-wal display.sqlite-shm cloud-ack.txt'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# One Nucleo held halted with its watchdog frozen, so its firmware does not run until release().
class Nucleo:
    def __init__(self, node, unique_id):
        self.node, self.unique_id, self.session = node, unique_id, None

    def _read_state(self):
        return bytes(self.session.target.read_memory_block8(STATE_START, STATE_SIZE))

    def halt(self):
        from pyocd.core.helpers import ConnectHelper
        from pyocd.core.target import Target
        self.session = ConnectHelper.session_with_chosen_probe(
            unique_id=self.unique_id, blocking=False,
            options={'target_override': TARGET, 'connect_mode': 'under-reset'})
        self.session.open()
        target = self.session.target
        region = target.memory_map.get_region_for_address(STATE_START)
        # Connecting under reset does not leave the core halted on these boards
        # (seen on every backup on November 16-18). Halt it, and freeze the
        # independent watchdog while halted (DBGMCU_APB1_FZ bit 12) so it
        # cannot reset the MCU mid-read. A watchdog reset can land between
        # the two, so retry.
        for _ in range(5):
            target.halt()
            target.write32(DBGMCU_APB1_FZ, target.read32(DBGMCU_APB1_FZ) | IWDG_STOP)
            if target.get_state() == Target.State.HALTED:
                break
        else:
            raise RuntimeError(f'{self.node} did not halt')
        if target.read16(FLASH_KIB_REGISTER) != FLASH_KIB:
            raise RuntimeError(f'{self.node} is not a {FLASH_KIB} KiB part; refusing to erase')
        if not (region and region.is_flash and region.contains_range(STATE_START, length=STATE_SIZE)):
            raise RuntimeError(f'{self.node} state range is not one flash region; refusing to erase')

    # Two identical reads, so a bad debug read cannot become the only copy of a history.
    def backup(self, directory):
        data = self._read_state()
        if data != self._read_state():
            raise RuntimeError(f'{self.node} state readback is not repeatable')
        path = directory / f'{self.node}-{self.unique_id[-6:]}-state.bin'
        path.write_bytes(data)
        if path.read_bytes() != data:
            raise RuntimeError(f'{path} does not match what was read')
        LOG.info('%s state saved to %s (sha256 %s)', self.node, path, sha256(data))

    def erase(self):
        from pyocd.flash.eraser import FlashEraser
        FlashEraser(self.session, FlashEraser.Mode.SECTOR).erase([(STATE_START, STATE_START + STATE_SIZE)])
        if self._read_state().strip(b'\xff'):
            raise RuntimeError(f'{self.node} state region is not blank after erase')
        LOG.info('%s sectors 6-7 erased and blank', self.node)

    # Hardware reset: software reset fails on these boards (see doc/LAB3_CAN_BRINGUP.md).
    def release(self):
        from pyocd.core.target import Target
        if self.session is None:
            return
        try:
            if self.session.is_open:
                self.session.target.reset(Target.ResetType.HARDWARE)
        finally:
            self.session.close()
            self.session = None
        LOG.info('%s released', self.node)


# The Pi cockpit service and its store, driven over the `wheelpi` SSH alias.
class Pi:
    def __init__(self, stamp):
        self.backup_dir = f'{PI_STATE}/pristine-backup-{stamp}'
        self.log_offset = 0

    def run(self, command, timeout=60):
        result = call(SSH + [command], capture_output=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError(f'Pi: {command}: {result.stderr.decode().strip() or result.stdout.decode().strip()}')
        return result.stdout.decode()

    # Latest STATUS line the cockpit wrote after `log_offset` bytes of its service log.
    def status(self):
        lines = self.run(f'tail -c +{self.log_offset + 1} {PI_STATE}/service.log | grep -a ^STATUS | tail -n 2; true')
        for line in reversed(lines.splitlines()):
            try:
                return json.loads(line[7:])
            except json.JSONDecodeError:
                continue  # the newest line was still being written
        return None

    # Later status() calls see only what the cockpit logs from here on (or the last `back` bytes).
    def mark(self, back=0):
        self.log_offset = max(0, int(self.run(f'stat -c %s {PI_STATE}/service.log')) - back)

    def stop(self):
        sudo(sudo_password(), f'systemctl stop {UNIT}')
        self.mark()

    # Copies the stopped store beside itself on the Pi, then here, and checks every hash.
    def backup(self, directory):
        name = Path(self.backup_dir).name
        listing = self.run(
            f'set -e; cd {PI_STATE}; test -f raft.bin; mkdir {name}; '
            f'for f in {PI_FILES}; do if [ -e $f ]; then cp -p $f {name}/; fi; done; '
            f'cd {name}; sha256sum *')
        copy = call(['scp', '-o', 'BatchMode=yes', '-r', f'wheelpi:{self.backup_dir}', str(directory / 'pi')],
                    capture_output=True, timeout=120)
        if copy.returncode:
            raise RuntimeError(f'Pi backup copy failed: {copy.stderr.decode().strip()}')
        for line in listing.splitlines():
            digest, name = line.split()
            if sha256((directory / 'pi' / name.lstrip('*')).read_bytes()) != digest:
                raise RuntimeError(f'Pi backup {name} does not match the Pi copy')
        LOG.info('Pi state saved to %s and on the Pi in ~/%s', directory / 'pi', self.backup_dir)

    def clear(self):
        self.run(f'cd {PI_STATE} && rm -f {PI_FILES}')
        LOG.info('Pi store cleared')

    def start(self):
        sudo(sudo_password(), f'systemctl start {UNIT}')

    # Poll fresh STATUS lines until `problems(status)` is empty; returns the last status seen.
    def wait(self, problems, seconds):
        deadline = time.monotonic() + seconds
        while True:
            status = self.status()
            if not problems(status) or time.monotonic() >= deadline:
                return status
            time.sleep(0.5)


# What stops the Pi from being the cold-start leader the Nucleos must hear when they boot.
def leader_problems(status):
    if status is None:
        return ['no STATUS line from the restarted cockpit']
    raft = status['raft']
    found = []
    if raft['role'] != 2 or raft['leader'] != 1:
        found.append(f"Pi is not leader (role {raft['role']}, leader N{raft['leader']})")
    if raft['term'] != 1:
        found.append(f"term is {raft['term']}, not 1")
    if raft['failed']:
        found.append('Pi Raft store failed')
    return found


# What separates the cluster from checkoff step 1's cold start; cockpit ERROR without the proxy is expected.
def cold_start_problems(status):
    found = leader_problems(status)
    if status is None:
        return found
    raft = status['raft']
    found += [f'{name} is not alive on CAN' for name in ('N2', 'N3') if not status['alive'].get(name)]
    if raft['nodes'] != 7:
        found.append(f"committed node set is {raft['nodes']:#x}, not 0x7")
    if raft['links'] != 63:
        found.append(f"committed CAN links are {raft['links']:#x}, not all six (0x3f)")
    return found


# The whole procedure. Returns the settled Pi status; raises if the Pi never led term 1.
def wipe(nucleos, pi, directory):
    pi.stop()
    try:
        for nucleo in nucleos:
            nucleo.halt()
        # All three nodes are now down. Every backup must succeed before anything is erased.
        for nucleo in nucleos:
            nucleo.backup(directory)
        pi.backup(directory)
        for nucleo in nucleos:
            nucleo.erase()
        pi.clear()
        pi.start()
        problems = leader_problems(pi.wait(leader_problems, 30))
        if problems:
            raise RuntimeError('Pi did not become the cold-start leader: ' + '; '.join(problems))
    except BaseException:
        try:
            pi.start()  # idempotent; a failed wipe must not leave the cockpit down
        except Exception:
            LOG.exception('Could not restart %s', UNIT)
        raise
    finally:
        for nucleo in nucleos:
            try:
                nucleo.release()
            except Exception:
                LOG.exception('Could not release %s; press its reset button', nucleo.node)
    return pi.wait(cold_start_problems, 15)


def find_nucleos():
    from pyocd.core.helpers import ConnectHelper
    connected = [probe.unique_id for probe in
                 ConnectHelper.get_all_connected_probes(blocking=False, print_wait_message=False)]
    nucleos = []
    for ending, node in PROBES.items():
        matches = [unique_id for unique_id in connected if unique_id.endswith(ending)]
        if len(matches) != 1:
            raise RuntimeError(f'ST-LINK ending {ending} ({node}) is not connected; found {connected}')
        nucleos.append(Nucleo(node, matches[0]))
    return nucleos


def main():
    parser = argparse.ArgumentParser(description='Back up and wipe all three Lab 5 Raft histories, '
                                     'then cold-start the cluster with the Pi leading term 1.')
    parser.add_argument('--yes', action='store_true', help='Skip the WIPE confirmation')
    args = parser.parse_args()
    stamp = time.strftime('%Y%m%d-%H%M%S')
    directory = REPO / 'logs/lab5/pristine' / stamp
    directory.mkdir(parents=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s',
                        handlers=[logging.FileHandler(directory / 'pristine.log', encoding='utf-8'),
                                  logging.StreamHandler()])
    try:
        nucleos = find_nucleos()
        pi = Pi(stamp)
        pi.mark(back=20000)
        raft = (pi.status() or {}).get('raft', {})
        print(f"This erases the Raft history on the Pi, N2 and N3 (now term {raft.get('term')}, "
              f"{raft.get('length')} entries) after backing all three up to\n  {directory}\n"
              'Both Nucleos reset; wheels can move.')
        if not args.yes and input('Type WIPE to continue: ') != 'WIPE':
            print('Nothing changed.')
            return 1
        status = wipe(nucleos, pi, directory)
        problems = cold_start_problems(status)
        raft = status['raft'] if status else {}
        LOG.info('%s | leader N%s, term %s, commit %s, error %s, wheel input %s | backups %s',
                 'COLD START OK' if not problems else 'NOT A CLEAN COLD START: ' + '; '.join(problems),
                 raft.get('leader'), raft.get('term'), raft.get('commit'),
                 status and status['error'], status and status['udp_ok'], directory)
        return 1 if problems else 0
    except Exception:
        LOG.exception('Pristine reset failed; see %s', directory / 'pristine.log')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
