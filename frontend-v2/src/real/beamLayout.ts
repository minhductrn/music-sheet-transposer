import {Beam,Pitch,type Note,type OpenSheetMusicDisplay} from 'opensheetmusicdisplay';

/** XML append order can differ from time order after dragging a note.
 * Rebuild explicit beams on this renderer instance, without changing saved XML. */
export function restoreExplicitBeams(osmd:OpenSheetMusicDisplay,xml:string){
    let rebuilt=false;
    const doc=new DOMParser().parseFromString(xml,'application/xml');
    const children=(e:Element,n:string)=>[...e.children].filter(c=>c.localName===n);
    const text=(e:Element,n:string,f='')=>children(e,n)[0]?.textContent??f;
    children(doc.documentElement,'part').forEach((part,pi)=>{
        let divisions=1;
        children(part,'measure').forEach((measure,mi)=>{
            const source=osmd.Sheet.SourceMeasures[mi];if(!source)return;
            const available=source.VerticalSourceStaffEntryContainers.flatMap(c=>c.StaffEntries.filter(Boolean).flatMap(s=>s.VoiceEntries.flatMap(v=>v.Notes))).filter(n=>n.ParentStaff.ParentInstrument===osmd.Sheet.Instruments[pi]);
            const claimed=new Set<Note>();
            const marked:{note:Note;onset:number;voice:string;staff:number;mark:string}[]=[];
            let cursor=0,previous=0;
            for(const node of measure.children){
                if(node.localName==='attributes'){divisions=Number(text(node,'divisions',String(divisions)));continue;}
                if(node.localName==='backup'||node.localName==='forward'){cursor+=Number(text(node,'duration','0'))/divisions*(node.localName==='backup'?-1:1);continue;}
                if(node.localName!=='note')continue;
                const onset=children(node,'chord').length?previous:cursor;
                previous=onset;if(!children(node,'chord').length&&!children(node,'grace').length)cursor+=Number(text(node,'duration','0'))/divisions;
                const pitch=children(node,'pitch')[0],voice=text(node,'voice','1'),staff=Number(text(node,'staff','1'));
                const note=available.find(n=>!claimed.has(n)&&String(n.ParentVoiceEntry.ParentVoice.VoiceId)===voice&&n.ParentStaff.ParentInstrument.Staves.indexOf(n.ParentStaff)+1===staff&&Math.abs(n.ParentVoiceEntry.Timestamp.RealValue*4-onset)<1e-7&&(pitch?!!n.Pitch&&Pitch.getNoteEnumString(n.Pitch.FundamentalNote)===text(pitch,'step')&&n.Pitch.Octave+Pitch.OctaveXmlDifference===Number(text(pitch,'octave'))&&n.Pitch.AccidentalHalfTones===Number(text(pitch,'alter','0')):n.isRest()));
                if(!note)continue;claimed.add(note);
                const beam=children(node,'beam').find(b=>(b.getAttribute('number')??'1')==='1');
                if(beam)marked.push({note,onset,voice,staff,mark:beam.textContent??''});
            }
            const pending=new Map<string,Note[]>();
            for(const item of marked.sort((a,b)=>a.onset-b.onset)){
                const key=item.voice+'|'+item.staff;
                if(item.mark==='begin')pending.set(key,[item.note]);
                else if(item.mark==='continue'||item.mark==='end'){
                    const notes=pending.get(key);if(!notes)continue;notes.push(item.note);
                    if(item.mark==='end'){
                        const beam=new Beam(1);for(const note of notes)beam.addNoteToBeam(note);rebuilt=true;
                        pending.delete(key);
                    }
                }
            }
        });
    });
    return rebuilt;
}
