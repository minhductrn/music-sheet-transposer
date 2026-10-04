import { useEffect, useRef, useState } from 'react'
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay'
import type { ScoreSelection } from '../types/review'

interface MusicSheetViewerProps {
  musicXml: Blob | null
  title?: string
  selection?: ScoreSelection | null
}

export default function MusicSheetViewer({
  musicXml,
  title = 'Transposed Sheet Music',
  selection = null,
}: MusicSheetViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [failedXml, setFailedXml] = useState<Blob | null>(null)
  const osmdRef = useRef<OpenSheetMusicDisplay | null>(null)
  const selectionRef = useRef<ScoreSelection | null>(selection)

  function identify(osmd: OpenSheetMusicDisplay, selected: ScoreSelection | null) {
    const cursor = osmd.cursor
    if (!cursor) return
    cursor.hide()
    if (!selected || selected.onset === null) return
    const [numerator, denominator = '1'] = selected.onset.split('/')
    const target = Number(numerator) / Number(denominator) / 4 // OSMD uses whole-note units.
    if (!Number.isFinite(target) || target < 0) return
    cursor.reset()
    // Public cursor/iterator API, bounded even when unusual notation does not expose an entry.
    for (let steps = 0; steps < 100_000 && !cursor.iterator.EndReached; steps++) {
      const iterator = cursor.iterator
      const measure = iterator.CurrentMeasureIndex
      const position = iterator.CurrentRelativeInMeasureTimestamp.RealValue
      if (measure === selected.measureIndex && Math.abs(position - target) < 0.000001) {
        cursor.show()
        return
      }
      if (measure > selected.measureIndex || (measure === selected.measureIndex && position > target)) return
      cursor.next()
    }
  }

  useEffect(() => {
    selectionRef.current = selection
    if (osmdRef.current) identify(osmdRef.current, selection)
  }, [selection])

  useEffect(() => {
    if (!musicXml || !containerRef.current) {
      return
    }

    const musicXmlBlob = musicXml
    let cancelled = false
    let resizeObserver: ResizeObserver | undefined

    async function renderMusicSheet() {
      const xml = await musicXmlBlob.text()

      if (cancelled || !containerRef.current) {
        return
      }

      containerRef.current.innerHTML = ''

      const osmd = new OpenSheetMusicDisplay(
        containerRef.current,
        {
          autoResize: false,
          backend: 'svg',
          drawTitle: true,
          disableCursor: false,
        },
      )

      // A Document also handles valid XML without a declaration; strings can be interpreted as URLs.
      await osmd.load(new DOMParser().parseFromString(xml, 'application/xml'))

      if (!cancelled) {
        osmd.render()
        osmdRef.current = osmd
        identify(osmd, selectionRef.current)
        let width = containerRef.current!.clientWidth
        resizeObserver = new ResizeObserver(([entry]) => {
          if (cancelled || entry.contentRect.width === width) return
          width = entry.contentRect.width
          try {
            osmd.updateGraphic() // Recalculate beams and layout for the changed container width.
            osmd.render()
            identify(osmd, selectionRef.current)
          } catch (error) {
            setFailedXml(musicXmlBlob)
            console.error('Unable to resize MusicXML preview:', error)
          }
        })
        resizeObserver.observe(containerRef.current!)
      }
    }

    renderMusicSheet().catch((error) => {
      if (!cancelled) setFailedXml(musicXmlBlob)
      console.error('Unable to render MusicXML:', error)
    })

    return () => {
      cancelled = true
      resizeObserver?.disconnect()
      osmdRef.current?.cursor?.hide()
      osmdRef.current = null
    }
  }, [musicXml])

  if (!musicXml) {
    return null
  }

  return (
    <div>
      <h2>{title}</h2>
      {selection && <p className="review-selection" role="status">Selected: {selection.label}. The cursor identifies its rhythmic position; simultaneous notes share the cursor.</p>}
      {failedXml === musicXml && (
        <p role="alert">Unable to preview this MusicXML. Recognition may have produced unsupported notation.</p>
      )}
      <div ref={containerRef} />
    </div>
  )
}
