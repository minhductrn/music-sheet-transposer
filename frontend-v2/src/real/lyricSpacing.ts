import type {OpenSheetMusicDisplay} from 'opensheetmusicdisplay';

/** Position lyrics before system spacing: below the notation, using the former third-verse row as the first-row reference below the lowest
 * note-bearing staff/ledger line, with top-aligned rows for all verses.
 * This changes disposable engraving objects only, never saved lyric content.
 */
export function spaceLyricRows(osmd:OpenSheetMusicDisplay){
    type Measure=OpenSheetMusicDisplay['GraphicSheet']['MeasureList'][number][number];
    type Line=NonNullable<Measure>['ParentStaffLine'];
    type Entry=NonNullable<Measure>['staffEntries'][number];
    type Calculator={calculateSingleStaffLineLyricsPosition:(line:Line,verses:string[])=>Entry[]};
    const calculator=osmd.GraphicSheet.GetCalculator as unknown as Calculator;
    calculator.calculateSingleStaffLineLyricsPosition=function(line,verses){
        const entries=line.Measures.flatMap(m=>m.staffEntries);
        const lyricEntries=entries.filter(e=>e.LyricsEntries.length>0);
        if(!lyricEntries.length)return [];
        const spacing=line.StaffLines.length>1?Math.abs(line.StaffLines[1].Start.y-line.StaffLines[0].Start.y):1;
        let lowest=line.StaffHeight;
        for(const entry of entries)for(const voice of entry.graphicalVoiceEntries)for(const note of voice.notes){
            if(note.sourceNote.isRest())continue;
            const y=entry.PositionAndShape.RelativePosition.y+voice.PositionAndShape.RelativePosition.y+note.PositionAndShape.RelativePosition.y;
            if(Number.isFinite(y))lowest=Math.max(lowest,y);
        }
        for(const entry of lyricEntries)for(const lyric of entry.LyricsEntries){
            const label=lyric.GraphicalLabel;
            label.Label.textAlignment-=label.Label.textAlignment%3;
            label.setLabelPositionAndShapeBorders();
        }
        const rowStep=osmd.EngravingRules.LyricsHeight+spacing*0.35;
        // User reference: place verse 1 at the former verse-3 ("tầng") row.
        // Do not renumber, merge or delete the imported extra verses.
        const top=Math.ceil((lowest-1e-7)/spacing)*spacing+3*spacing+2*rowStep;
        const rows=[...new Set(lyricEntries.flatMap(e=>e.LyricsEntries.map(l=>String(l.LyricsEntry.VerseNumber))))].sort((a,b)=>verses.indexOf(a)-verses.indexOf(b));
        const heights=rows.map(verse=>Math.max(...lyricEntries.flatMap(e=>e.LyricsEntries.filter(l=>String(l.LyricsEntry.VerseNumber)===verse).map(l=>l.GraphicalLabel.PositionAndShape.BorderBottom-l.GraphicalLabel.PositionAndShape.BorderTop)),osmd.EngravingRules.LyricsHeight));
        let bottom=top;
        for(const entry of lyricEntries)for(const lyric of entry.LyricsEntries){
            const label=lyric.GraphicalLabel,box=label.PositionAndShape,index=rows.indexOf(String(lyric.LyricsEntry.VerseNumber));
            const rowTop=top+heights.slice(0,index).reduce((sum,height)=>sum+height+spacing*0.35,0);
            box.RelativePosition.y=rowTop-box.BorderTop;
            label.Label.fontStyle=lyric.LyricsEntry.FontStyle;
            bottom=Math.max(bottom,rowTop+heights[index]);
        }
        line.SkyBottomLineCalculator.updateBottomLineInRange(0,line.PositionAndShape.Size.width,bottom+spacing);
        return lyricEntries;
    };
}
