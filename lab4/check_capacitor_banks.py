"""Calculate the revised capacitor-bank sensitivity; no hardware result claimed."""
from pathlib import Path
import csv,hashlib,json,math

ROOT=Path(__file__).resolve().parent
MPN='GRM32ER61E226KE15L'
with (ROOT/'KiCad/Circuit-BOM.csv').open(encoding='utf-8-sig',newline='') as f:
    parts={r['Reference']:r for r in csv.DictReader(f)}
rows=[]
for i,(rail,vmax,bias_loss) in enumerate([('SERVO',6.82,.40),('5V',5.19,.25),('3V3',3.38,.20)]):
    base=410+10*i
    inputs=[f'C{base}',f'C{base+5}',f'C{base+6}']
    outputs=[f'C{base+2}',f'C{base+3}',f'C{base+7}']+([f'C{base+8}'] if i==0 else [])
    for ref in inputs+outputs:
        assert parts[ref]['MPN']==MPN,ref
        assert parts[ref]['Footprint']=='Capacitor_SMD:C_1210_3225Metric',ref
    multiplier=.9*.85*.8 # tolerance, temperature, extra aging sensitivity
    cin_15=22*len(inputs)*.30*multiplier
    cout=22*len(outputs)*(1-bias_loss)*multiplier
    target=1e6/((2*math.pi*20000)**2*2.63e-6)
    assert cin_15>10 and cout>target
    rows.append(dict(rail=rail,input_refs=inputs,output_refs=outputs,
        nominal_input_uF=22*len(inputs),nominal_output_uF=22*len(outputs),
        output_voltage_screen_V=vmax,assumed_output_bias_loss_fraction=bias_loss,
        screened_input_uF_at_15V=round(cin_15,4),
        screened_input_uF_at_12p6V=round(22*len(inputs)*.35*multiplier,4),
        screened_output_uF=round(cout,4),
        output_target_uF_at_2p63uH_20kHz=round(target,4),
        screened_LC_pole_kHz_at_2p63uH=round(1/(2*math.pi*math.sqrt(2.63e-6*cout*1e-6))/1000,3),
        nominal_output_charge_current_A_at_1p6ms_ramp=round(22*len(outputs)*1e-6*vmax/.0016,4)))
report=dict(status='PASS for the stated capacitance sensitivity; not loop or hardware qualification',
    mpn=MPN,quantity=19,package='1210',rated_voltage_V=25,
    sources=['https://static.chipdip.ru/lib/973/DOC031973461.pdf',
             'https://www.ti.com/lit/ds/symlink/tps564252.pdf'],
    assumptions={'tolerance_multiplier':.9,'temperature_multiplier':.85,
                 'aging_multiplier_assumed':.8,'input_bias_loss_at_15V_assumed':.70,
                 'input_bias_loss_at_12p6V_assumed':.65},
    banks=rows,limitations=[
        'Bias-loss factors are conservative rounded readings of a typical manufacturer plot, not guaranteed limits.',
        'Multiplication of independent temperature/tolerance/aging factors is a sensitivity, not an approval-sheet combined minimum.',
        '20kHz is TI design guidance for the LC pole, not a pass/fail stability boundary.',
        'No claim of full-loop phase margin, ripple heating, transient response or hardware operation.'],
    source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['KiCad/Circuit-BOM.csv','KiCad/Power.kicad_sch']})
(ROOT/'Capacitor-bank-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,indent=2))
