import { useEffect, useRef } from 'react'
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay'

interface MusicSheetViewerProps {
  musicXml: Blob | null
}

export default function MusicSheetViewer({
  musicXml,
}: MusicSheetViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!musicXml || !containerRef.current) {
      return
    }

    const musicXmlBlob = musicXml
    let cancelled = false

    async function renderMusicSheet() {
      const xml = await musicXmlBlob.text()

      if (cancelled || !containerRef.current) {
        return
      }

      containerRef.current.innerHTML = ''

      const osmd = new OpenSheetMusicDisplay(
        containerRef.current,
        {
          autoResize: true,
          backend: 'svg',
          drawTitle: true,
        },
      )

      await osmd.load(xml)

      if (!cancelled) {
        osmd.render()
      }
    }

    renderMusicSheet().catch((error) => {
      console.error('Unable to render MusicXML:', error)
    })

    return () => {
      cancelled = true
    }
  }, [musicXml])

  if (!musicXml) {
    return null
  }

  return (
    <div>
      <h2>Transposed Sheet Music</h2>
      <div ref={containerRef} />
    </div>
  )
}