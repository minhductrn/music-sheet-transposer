/** Local MusicXML is durable; review sessions and file handles are temporary. */
export interface ScoreFileHandle {
  name: string
  createWritable(): Promise<{ write(data: Blob): Promise<void>; close(): Promise<void>; abort(): Promise<void> }>
}

export interface SavedScoreFile {
  reviewId: string
  revision: number
  blob: Blob
  filename: string
}

interface SaveBrowser {
  showSaveFilePicker?: (options: unknown) => Promise<ScoreFileHandle>
  prompt: (message: string, value: string) => string | null
}

export async function chooseScoreFile(saveAs: boolean, handle: ScoreFileHandle | null, filename: string,
  browser: SaveBrowser = window as unknown as SaveBrowser) {
  if (!saveAs && handle) return { handle, filename: handle.name }
  // Invoke the picker before network awaits, while the click still has user activation.
  if (browser.showSaveFilePicker) {
    const selected = await browser.showSaveFilePicker({ suggestedName: filename,
      types: [{ description: 'MusicXML score', accept: { 'application/vnd.recordare.musicxml+xml': ['.musicxml'] } }] })
    return { handle: selected, filename: selected.name }
  }
  const name = saveAs ? browser.prompt('Save MusicXML as (destination is controlled by browser download settings):', filename) : filename
  if (name === null) return null
  const safeName = name.trim().replace(/[\\/]/g, '_')
  if (!safeName) throw new Error('Enter a filename for the MusicXML score.')
  return { handle: null, filename: /\.(musicxml|xml)$/i.test(safeName) ? safeName : `${safeName}.musicxml` }
}

export async function writeScoreFile(blob: Blob, target: { handle: ScoreFileHandle | null; filename: string },
  download: (blob: Blob, filename: string) => void): Promise<'written' | 'download-requested'> {
  if (!target.handle) {
    download(blob, target.filename)
    return 'download-requested'
  }
  const stream = await target.handle.createWritable()
  try {
    await stream.write(blob)
    await stream.close()
    return 'written'
  } catch (error) {
    await stream.abort().catch(() => {})
    throw error
  }
}

export function isSavedRevision(saved: SavedScoreFile | null | undefined, review: { id: string; revision: number }) {
  return saved?.reviewId === review.id && saved.revision === review.revision
}
