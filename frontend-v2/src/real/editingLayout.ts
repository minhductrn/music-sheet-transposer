import type { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';

type Ticks = { numerator:number; denominator:number; clone:()=>Ticks };
type LayoutVoice = {getTicksUsed:()=>Ticks};
type LayoutMeasure = {vfVoices?:Record<string,LayoutVoice>};
type Calculator = {calculateMeasureXLayout:(measures:LayoutMeasure[])=>number};

/** VexFlow's formatter takes its time span from the first voice, even when a
 * later voice extends farther. Align the disposable layout getters to the
 * longest voice before width calculation. Tickables and their timestamps,
 * musical voice durations, time signatures and canonical MusicXML stay intact.
 * This adapter is scoped to one renderer instance, never a global prototype.
 */
export function expandEditingMeasures(osmd:OpenSheetMusicDisplay){
    const calculator=osmd.GraphicSheet.GetCalculator as unknown as Calculator;
    const original=calculator.calculateMeasureXLayout;
    calculator.calculateMeasureXLayout=function(measures){
        const voices=measures.flatMap(m=>Object.values(m.vfVoices??{}));
        const value=(t:Ticks)=>t.numerator/t.denominator;
        if(voices.length){
            let extent=voices[0].getTicksUsed().clone();
            for(const voice of voices){const used=voice.getTicksUsed();if(value(used)>value(extent))extent=used.clone();}
            for(const voice of voices)if(value(extent)>value(voice.getTicksUsed())+1e-7)voice.getTicksUsed=()=>extent.clone();
        }
        return original.call(this,measures);
    };
}
