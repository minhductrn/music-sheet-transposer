import { useEffect, useRef, useState } from 'react'
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay'

interface MusicSheetViewerProps {
  musicXml: Blob | null
  title?: string
}

export default function MusicSheetViewer({
  musicXml,
  title = 'Transposed Sheet Music',
}: MusicSheetViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [failedXml, setFailedXml] = useState<Blob | null>(null)

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
      if (!cancelled) setFailedXml(musicXmlBlob)
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
      <h2>{title}</h2>
      {failedXml === musicXml && (
        <p role="alert">Unable to preview this MusicXML. Recognition may have produced unsupported notation.</p>
      )}
      <div ref={containerRef} />
    </div>
  )
}
