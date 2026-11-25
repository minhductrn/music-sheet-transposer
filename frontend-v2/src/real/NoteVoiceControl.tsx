import {useEffect,useRef,useState} from 'react';

type Props={voice:string;busy:boolean;allowCurrent?:boolean;onChange:(voice:string)=>Promise<void>};

/** One shared, directly editable voice control for Concert and instrument scores. */
export function NoteVoiceControl({voice,busy,allowCurrent=false,onChange}:Props){
    const [value,setValue]=useState(voice),applying=useRef(false);
    useEffect(()=>setValue(voice),[voice]);
    async function apply(){
        const next=value.trim();if(applying.current||busy||!next||(next===voice&&!allowCurrent))return;
        applying.current=true;
        try{await onChange(next);}finally{applying.current=false;}
    }
    return <fieldset className="note-voice-control" disabled={busy}>
        <legend>Voice / Part</legend>
        <form className="note-voice-form" onSubmit={e=>{e.preventDefault();void apply();}}>
            <label>Voice<input aria-label="Selected event voice" inputMode="numeric" value={value} onChange={e=>setValue(e.target.value)} onBlur={()=>void apply()} size={4}/></label>
            <button type="submit" disabled={!value.trim()||(value.trim()===voice&&!allowCurrent)}>Apply</button>
            <output aria-label="Current note voice">Voice {voice} · {voice==='1'?'Main':voice==='2'?'Harmony':'Part '+voice}</output>
        </form>
        <small>1 = Main · 2 = Harmony</small>
    </fieldset>;
}
