"""Load-specific prototype planning screen; not a fault or transient certification.

Run with KiCad Python. Reuses the saved-board conductor graph and evaluated
Pi mesh. Numerical assumptions are emitted alongside every result. Nothing
in this calculation changes CAD or constitutes an authorization to order.
"""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import math
import runpy
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    board_hash = sha(ROOT/'KiCad/Lab4.kicad_pcb')
    operating = json.loads((ROOT/'Pi-operating-mesh-check.json').read_text())
    stress = json.loads((ROOT/'Pi-feed-mesh-check.json').read_text())
    assert operating['board_sha256'] == stress['board_sha256'] == board_hash
    assert operating['allocation_sha256'] == stress['allocation_sha256'] == sha(ROOT/'Load-allocation-check.json')
    assert operating['assumptions']['Pi_current_A'] == 1.5
    assert stress['assumptions']['Pi_current_A'] == 3.0
    a = min(operating['results'], key=lambda x:x['mesh_mm'])
    b = min(stress['results'], key=lambda x:x['mesh_mm'])
    assert a['mesh_mm'] == b['mesh_mm'] == .05
    slope = (b['positive_feed_drop_V']['J70']-a['positive_feed_drop_V']['J70'])/1.5
    intercept = a['positive_feed_drop_V']['J70']-1.5*slope
    assert slope > 0 and intercept >= -1e-6
    allocation = json.loads((ROOT/'Load-allocation-check.json').read_text())
    source_v = allocation['five_volt']['source_minimum_V']
    pi_cases = []
    for amps, label in [(1.25,'published workload example'),(1.5,'sustained planning allowance'),
                        (2.0,'brief higher-load sensitivity'),(3.0,'deferred sustained stress case')]:
        drop = intercept+slope*amps
        for contact in (.010,.020):
            # Contact allowance includes an illustrative lead/contact budget;
            # seven ground contacts are assumed to share equally.
            terminal=source_v-drop*(1+.00393*(80-20))-amps*contact*(1+1/7)-.020
            pi_cases.append(dict(case=label,Pi_A=amps,source_min_V=source_v,
                copper_drop_20C_V=drop,copper_temperature_assumed_C=80,
                each_contact_and_lead_R_assumed_ohm=contact,ground_allowance_assumed_V=.020,
                terminal_before_transients_V=terminal,
                reserve_to_upper_warning_corner_V=terminal-4.8615))

    old_argv=sys.argv[:]
    with tempfile.TemporaryDirectory() as tmp:
        sys.argv=['check_load_allocation.py','--output',str(Path(tmp)/'load.json')]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                graph=runpy.run_path(str(ROOT/'check_load_allocation.py'))
        finally:
            sys.argv=old_argv
    tree,route,resistance,allocate=(graph[x] for x in ('tree','route','resistance','allocation'))
    p=graph['p']
    pre_paths=[('/Power/BAT_PLUS',('J40','1'),('F1','1')),
               ('/Power/BAT_FUSED',('F1','2'),('Q1','2'))]
    pre_r=sum(sum(resistance(tree(net,src)[0][i]) for i in route(net,src,tgt))
              for net,src,tgt in pre_paths)
    main_path=[]
    for net,src,tgt in pre_paths:
        items=tree(net,src)[0]
        for j in route(net,src,tgt):
            item=items[j]
            if item.Type()==p.PCB_TRACE_T:
                main_path.append(dict(net=net,width_mm=p.ToMM(item.GetWidth()),
                    length_mm=p.ToMM(item.GetLength()),layer=board_layer(p,item),
                    resistance_20C_ohm=resistance(item)))
    assert main_path and min(x['width_mm'] for x in main_path)>=2.5
    assert all(x['layer'] in ('F.Cu','B.Cu') for x in main_path)
    inputs=[]
    for pack in (10.5,11.1,12.6):
        for pi_a,servo,motor,label in [(1.5,.39,.72,'planning sustained'),
                                      (2.0,3.0,2.0,'brief simultaneous higher load')]:
            powers=[6.6*servo,5.1*(pi_a+.3),3.318*.8]
            local=[pack]*3
            for _ in range(80):
                branches=[power/(.8*v) for power,v in zip(powers,local)]
                total=motor+sum(branches)
                # 80C trace resistance, 20mOhm hot FET assumption, two
                # fuses at twice their typical cold R, and 30mOhm combined
                # harness/contact/return allowance. None is a rating.
                common_r=pre_r*1.2358+.020+2*.00742*2+.030
                source=pack-total*common_r
                loads=[('U80',['4'],motor,'aggregate motor supply assumption')]
                loads += [(f'U{40+i}',['1'],amps,'Pout/(local Vin*0.80)') for i,amps in enumerate(branches)]
                screen=allocate('/VBAT_PROTECTED',('Q1','3'),loads,source)
                local_new=[source-1.2358*next(x['shared_tree_drop_V'] for x in screen['loads'] if x['ref']==f'U{40+i}') for i in range(3)]
                if max(abs(x-y) for x,y in zip(local,local_new))<1e-8:break
                local=local_new
            else: raise ArithmeticError('Input iteration did not converge')
            assert min(local_new)>8
            items=tree('/VBAT_PROTECTED',('Q1','3'))[0]
            flows={}
            for load in screen['loads']:
                for j in route('/VBAT_PROTECTED',('Q1','3'),(load['ref'],load['pin'])):
                    flows[j]=flows.get(j,0)+load['allocation_A']
            conductors=[]
            for j,amps in flows.items():
                item=items[j]
                record=dict(id=item.m_Uuid.AsString(),current_A=amps,
                            loss_20C_W=amps**2*resistance(item))
                if item.Type()==p.PCB_TRACE_T:
                    record.update(kind='track',width_mm=p.ToMM(item.GetWidth()),
                        length_mm=p.ToMM(item.GetLength()),layer=board_layer(p,item))
                elif item.Type()==p.PCB_VIA_T:
                    record.update(kind='via',drill_mm=p.ToMM(item.GetDrill()))
                else:continue
                conductors.append(record)
            inputs.append(dict(case=label,pack_V=pack,Pi_A=pi_a,servo_A=servo,
                motors_aggregate_A=motor,input_A=total,converter_inputs_V=local_new,
                pre_FET_copper_loss_W=total**2*pre_r*1.2358,
                assumed_FET_loss_W=total**2*.020,
                two_fuse_loss_W=total**2*2*.00742*2,
                assumed_harness_contact_return_loss_W=total**2*.030,
                protected_input_conductors=conductors))

    # Loss sensitivity under intended sustained 5 V load, with no claim that
    # a brief peak is an allowed continuous temperature or fault condition.
    from check_power_margins import buck_scenario
    thermal=[]
    for vin in (10.5,12.6):
        for hot in (1.,2.):
            for overlap in (20,40):
                case=buck_scenario(vin,5.1,1.8,3.76e-6,600000,hot,overlap)
                thermal.append(case)
    # Servo average current must not be squared to estimate copper heating.
    # Apply the assumed 90/10 duty to I^2, and keep Eco-mode losses unmodeled.
    servo_rms=math.sqrt(.9*.1**2+.1*3**2)
    servo_high=buck_scenario(12.6,6.6,3,3.76e-6,600000,2,40)
    logic=buck_scenario(12.6,3.318,.8,3.76e-6,600000,2,40)
    trace_screens=[]
    for case in inputs:
        # TI SNVA766, section 11 / IPC-2221 external-trace approximation.
        # A steady empirical screen, not a transient or fuse-clearing model.
        for width in (1.2,2.5):
            area_mil2=(width/.0254)*(.035/.0254)
            rise=(case['input_A']/(.048*area_mil2**.725))**(1/.44)
            trace_screens.append(dict(case=case['case'],pack_V=case['pack_V'],
                input_A=case['input_A'],width_mm=width,copper_um=35,
                empirical_steady_rise_C_NOT_board_temperature=rise))
    out=dict(board_sha256=board_hash,calculation_only=True,
        electrical_design_basis='Bare Pi 4/car software; 1.5 A Pi sustained planning allowance, 0.3 A other 5 V allowance; 2 A Pi higher-load sensitivity; 3 A sustained is deferred',
        load_basis='1.5 A is an engineering allowance 20% above the dated official 1.25 A workload example, not a measured or guaranteed workload maximum',
        pi_feed_effective_ohm=slope,other_load_feed_drop_V=intercept,pi_cases=pi_cases,
        input_cases=inputs,pre_FET_copper_R_20C_ohm=pre_r,main_path=main_path,
        five_volt_sustained_loss_cases=thermal,
        servo_duty_assumption=dict(low_A=.1,low_fraction=.9,high_A=3,high_fraction=.1,
            average_A=.39,RMS_A=servo_rms,high_state_loss_case=servo_high,
            high_state_duty_weighted_modeled_loss_W=.1*servo_high['modeled_IC_loss_W_NOT_total'],
            limitation='High-state contribution only: light-load/Eco-mode losses, pulse duration and thermal cycling are unmodeled. This duty is not measured.'),
        logic_sustained_loss_case=logic,external_trace_screens=trace_screens,
        output_bank_charge_at_typical_softstart_A=66e-6*5.1/.0016,
        output_bank_charge_note='Nominal board bank only; excludes Pi onboard capacitance. Typical 1.6 ms soft-start is not guaranteed or an inrush test.',
        limits=['DC screens do not predict startup, ringing or load-step response.',
                'Pi input allowance must be checked during actual boot/car software before vehicle use.',
                'Thermal loss sensitivities are not junction-temperature predictions or guaranteed worst cases.',
                'The 10 A blade is removable. Final fuse/harness coordination is required before LiPo power, not a copper-geometry signoff from this script.',
                'No short-circuit survival or autonomous motor-protection claim. Current-limited bench commissioning is required before LiPo use.'],
        source_sha256={n:sha(ROOT/n) for n in ['KiCad/Lab4.kicad_pcb','Load-allocation-check.json','Pi-operating-mesh-check.json','Pi-feed-mesh-check.json','check_prototype_power.py','check_pi_feed.py']})
    (ROOT/'Prototype-power-check.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:out[k] for k in ['pi_feed_effective_ohm','other_load_feed_drop_V','pi_cases','input_cases']},indent=2))


def board_layer(p,item):
    return {p.F_Cu:'F.Cu',p.B_Cu:'B.Cu',p.In1_Cu:'In1.Cu',p.In2_Cu:'In2.Cu'}[item.GetLayer()]


if __name__=='__main__':main()
