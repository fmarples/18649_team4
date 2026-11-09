const text = (id, value) => document.getElementById(id).textContent = value;
async function refresh() {
  try {
    const response = await fetch('/api/state');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const s = await response.json(), h = s.heartbeat, r = h.raft || {};
    text('status', s.stale ? 'STALE — Pi/uplink heartbeat missing. Showing last known state.' : 'Vehicle heartbeat current');
    document.getElementById('status').className = s.stale ? 'stale' : 'live';
    text('leaders', `Leader: N${r.leader || '?'} · Time master: N${h.time_master || '?'} · Term: ${r.term ?? '?'}`);
    document.getElementById('nodes').replaceChildren(...[1,2,3].map(n => {
      const e = document.createElement('p');
      const known = Number.isInteger(r.nodes), bit = 1 << (n-1), a = 1 << (2*(n-1));
      e.textContent = `N${n}: ${!known ? 'unknown' : r.nodes & bit ? 'alive' : 'down'} · A: ${!known ? '?' : r.links & a ? 'up' : 'down'} · B: ${!known ? '?' : r.links & (a*2) ? 'up' : 'down'}`;
      return e;
    }));
    text('timing', `Global: ${h.global_us ?? '?'} µs · Last measured FL/RL offset: ${h.fl_offset_us ?? 'not measured'} / ${h.rl_offset_us ?? 'not measured'} µs`);
    text('held', `Held events: ${h.held_events ?? 'unknown while cockpit is absent'} · Uplink pending: ${h.pending ?? '?'} · Last ACK: ${h.last_ack ?? 'none'}`);
    text('missing', s.missing_entries ? `Mirror gap: ${s.missing_entries} entries fell outside the retained queue.` : 'No reported mirror gaps.');
    document.getElementById('events').replaceChildren(...s.entries.map(row => {
      const tr = document.createElement('tr');
      for (const v of [row.index,row.term,row.type,row.payload,row.global_time]) {
        const td = document.createElement('td'); td.textContent = v; tr.append(td);
      }
      return tr;
    }));
  } catch (e) { text('status', `DISCONNECTED — ${e.message}`); }
}
refresh(); setInterval(refresh,1000);
