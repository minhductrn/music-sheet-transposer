export type Handle = {
    createWritable: () => Promise<{
        write: (data: Blob) => Promise<void>;
        close: () => Promise<void>;
        abort?: () => Promise<void>;
    }>;
};
export function download(xml: string | Uint8Array, name: string) { const url = URL.createObjectURL(new Blob([typeof xml === 'string' ? xml : Uint8Array.from(xml)], { type: 'application/vnd.recordare.musicxml+xml' })); const a = document.createElement('a'); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
// Request the picker during the user's click, before awaiting backend validation.
export async function chooseLocal(name: string, handle: Handle | null, saveAs: boolean): Promise<Handle | null> { const picker = (window as Window & {
    showSaveFilePicker?: (options: unknown) => Promise<Handle>;
}).showSaveFilePicker; if (!picker)
    return null; return saveAs || !handle ? picker({ suggestedName: name, types: [{ description: 'MusicXML', accept: { 'application/vnd.recordare.musicxml+xml': ['.musicxml'] } }] }) : handle; }
export async function writeLocal(xml: string | Uint8Array, name: string, target: Handle | null): Promise<Handle | null> { if (!target) {
    download(xml, name);
    return null;
} const writer = await target.createWritable(); try {
    await writer.write(new Blob([typeof xml === 'string' ? xml : Uint8Array.from(xml)], { type: 'application/vnd.recordare.musicxml+xml' }));
    await writer.close();
}
catch (error) {
    await writer.abort?.().catch(() => { });
    throw error;
} return target; }
