import DirectLyricEditor from './DirectLyricEditor'
import { bindLyrics, currentLyric, type LyricBinding, type LyricScope } from '../utils/lyricInteraction'
import type { Lyric } from '../types/review'
import { correctionTieDocument } from '../utils/scoreTies'
import { standaloneTieScore, drawStandaloneTies } from '../utils/standaloneTies'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay'
import { bindRenderer, rendererOptions, reviewDocument } from '../utils/scoreRenderer'
import type { Score } from '../utils/visualReview'
import { amount } from '../utils/visualReview'
import ReviewScoreViewport from './ReviewScoreViewport'
import { engraveSourceGroups, initialEngravingWidth, trustedSourceGroups, sourceEngravingWidth, xmlSourceGroups } from '../utils/sourceEngraving'
import { insertionLanes, hitInsertion, scorePoint, drawInsertionMarker, renderedScorePages, insertionDiagnosticsEnabled, logInsertionDiagnostic, type VisualInsertionPosition } from '../utils/scoreInsertion'
import type { Pitch, ScoreSelection } from '../types/review'

interface MusicSheetViewerProps {
  lyricScope?: LyricScope
  onLyricApply?: (binding: LyricBinding, text: string) => Promise<{ lyric: Lyric; reviewId: string; revision: number }>
  onLyricOwnerSelect?: (lyricId: string | null) => void
  musicXml: Blob | null
  title?: string
  headerActions?: ReactNode
  toolbar?: ReactNode
  selection?: ScoreSelection | null
  score?: Score
  onSelect?: (id: string) => void
  onPitchDrop?: (id: string, pitch: Pitch) => void
  tieTargetIds?: string[] | null
  interactive?: boolean
  insertionMode?: boolean
  insertionPosition?: VisualInsertionPosition | null
  onPositionSelect?: (position: VisualInsertionPosition | null) => void
}

export default function MusicSheetViewer({
  musicXml,
  title = 'My Score',
  headerActions, toolbar,
  selection = null,
  lyricScope, onLyricApply, onLyricOwnerSelect,
  score, onSelect, onPitchDrop, tieTargetIds = null, interactive = true, insertionMode = false, insertionPosition = null, onPositionSelect,
}: MusicSheetViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [failedXml, setFailedXml] = useState<Blob | null>(null)
  const osmdRef = useRef<OpenSheetMusicDisplay | null>(null)
  const sourceGroups = trustedSourceGroups(score)
  const sourceReview = sourceGroups !== null
  const [engravingWidth, setEngravingWidth] = useState(initialEngravingWidth)
  const [groupingFailedXml, setGroupingFailedXml] = useState<Blob | null>(null)
  const selectionRef = useRef<ScoreSelection | null>(selection)

  const [lyricTarget, setLyricTarget] = useState<LyricBinding | null>(null)
  const [lyricMessage, setLyricMessage] = useState('')
  const lyricBindings = useRef<ReturnType<typeof bindLyrics> | null>(null)
  const renderGeneration = useRef(0)
  const interactionRef = useRef<ReturnType<typeof bindRenderer> | null>(null)
  const propsRef = useRef({ score, onSelect, onPitchDrop, tieTargetIds, interactive, insertionMode, insertionPosition, onPositionSelect, lyricScope, onLyricApply, onLyricOwnerSelect })
  const markerCleanup = useRef<(() => void) | null>(null)

  useEffect(() => {
    propsRef.current = { score, onSelect, onPitchDrop, tieTargetIds, interactive, insertionMode, insertionPosition, onPositionSelect, lyricScope, onLyricApply, onLyricOwnerSelect }
    interactionRef.current?.highlight(selection?.eventId ?? null, tieTargetIds)
    refreshMarker()
  }, [score, onSelect, onPitchDrop, tieTargetIds, interactive, selection, insertionMode, insertionPosition, onPositionSelect, lyricScope, onLyricApply, onLyricOwnerSelect])

  function bind(osmd: OpenSheetMusicDisplay) {
    interactionRef.current?.dispose()
    lyricBindings.current?.dispose()
    renderGeneration.current++
    const props = propsRef.current
    interactionRef.current = props.score && props.onSelect ? bindRenderer(osmd, props.score, (id) => {
      const latest = propsRef.current
      if (!latest.insertionMode && latest.interactive && (latest.tieTargetIds === null || latest.tieTargetIds.includes(id))) latest.onSelect?.(id)
    }, {
      enabled: () => { const p = propsRef.current; return Boolean(p.onPitchDrop && p.interactive && !p.insertionMode && p.tieTargetIds === null) },
      commit: (id, pitch) => propsRef.current.onPitchDrop?.(id, pitch),
    }) : null
    if (props.lyricScope && props.onLyricApply && containerRef.current) {
      lyricBindings.current = bindLyrics(osmd, containerRef.current, props.lyricScope, renderGeneration.current,
        () => propsRef.current.lyricScope ?? null,
        () => { const p = propsRef.current; return Boolean(p.interactive && !p.insertionMode && p.tieTargetIds === null && p.onSelect) },
        binding => { setLyricMessage(''); setLyricTarget(binding) })
    }
    interactionRef.current?.highlight(selectionRef.current?.eventId ?? null, props.tieTargetIds)
  }

  function refreshMarker() {
    markerCleanup.current?.(); markerCleanup.current = null
    const osmd = osmdRef.current
    const props = propsRef.current
    if (!osmd || !props.score || !props.insertionMode || !props.insertionPosition) return
    const lanes = insertionLanes(osmd, props.score).filter((p) => p.measureId === props.insertionPosition!.measureId && p.staff === props.insertionPosition!.staff && p.onset === props.insertionPosition!.onset)
    if (lanes.length !== 1) return
    const lane = lanes[0]
    const pages = renderedScorePages(osmd).filter((p) => p.page === lane.page)
    const svg = pages.length === 1 ? pages[0].svg : null
    if (svg) markerCleanup.current = drawInsertionMarker(svg, lane, osmd.Drawer.calculatePixelDistance(1))
  }

  function choosePosition(event: React.MouseEvent<HTMLDivElement>) {
    const osmd = osmdRef.current
    const props = propsRef.current
    if (!osmd || !props.score || !props.interactive || !props.insertionMode) return
    const target = event.target as Element
    if (insertionDiagnosticsEnabled()) {
      // Observe separately so diagnostics never replace the placement path below.
      try {
        const intercepted = Boolean(target.closest?.('[data-review-event]'))
        const svg = target.closest?.('svg') as SVGSVGElement | null
        const pages = renderedScorePages(osmd).filter((p) => p.svg === svg)
        const scale = osmd.Drawer.calculatePixelDistance(1)
        let failure = !svg ? 'missing-svg' : pages.length !== 1 ? 'non-unique-page'
          : !Number.isFinite(scale) || scale <= 0 ? 'invalid-pixels-per-unit' : null
        const point = !failure && svg ? scorePoint(svg, event.clientX, event.clientY, scale) : null
        if (!failure && !point) failure = 'svg-transform-conversion-failed'
        logInsertionDiagnostic({
          targetCategory: intercepted ? 'note event' : svg ? 'score SVG' : 'other',
          svgResolved: Boolean(svg), pageMatches: pages.length, page: pages.length === 1 ? pages[0].page : null,
          client: { x: event.clientX, y: event.clientY }, point, conversionFailure: failure,
          lanes: insertionLanes(osmd, props.score),
        })
      } catch { /* Diagnostics must never interrupt editing. */ }
    }
    const eventNode = target.closest?.('[data-review-event]')
    if (eventNode) {
      const id = eventNode.getAttribute('data-review-event')
      const matches = props.score.parts.flatMap((part) => part.measures.flatMap((measure) =>
        measure.voices.flatMap((voice) => voice.events.filter((note) => note.id === id)
          .map((note) => ({ measure, note })))))
      if (matches.length !== 1) { props.onPositionSelect?.(null); return }
      const { measure, note } = matches[0]
      if (note.kind === 'note' && note.pitch) {
        const valid = note.onset !== null && Number.isFinite(amount(note.onset)) && amount(note.onset) >= 0
          && note.staff !== null && Number.isInteger(note.staff) && note.staff >= 1 && note.staff <= measure.staves
        props.onPositionSelect?.(valid ? { measureId: measure.id, staff: note.staff!, onset: note.onset! } : null)
        return
      }
    }
    const svg = target.closest?.('svg') as SVGSVGElement | null
    const pages = renderedScorePages(osmd).filter((p) => p.svg === svg)
    if (!svg || pages.length !== 1) { props.onPositionSelect?.(null); return }
    const point = scorePoint(svg, event.clientX, event.clientY, osmd.Drawer.calculatePixelDistance(1))
    const lane = point ? hitInsertion(insertionLanes(osmd, props.score), pages[0].page, point) : null
    props.onPositionSelect?.(lane ? { measureId: lane.measureId, staff: lane.staff, onset: lane.onset } : null)
  }

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
    let standaloneCleanup: (() => void) | undefined
    let cancelWidthWait: (() => void) | undefined

    // Visibility changes do not change the Blob or remount the editing session.
    // OSMD reads offsetWidth, so wait for actual layout rather than CSS width.
    function waitForWidth(): Promise<boolean> {
      const container = containerRef.current
      if (cancelled || !container) return Promise.resolve(false)
      const pane = container.closest?.('.review-score-viewport')?.querySelector('.review-score-scroll')
      const measurable = () => {
        // An empty max-content surface has no intrinsic width yet.
        if (container.offsetWidth === 0 && pane && pane.clientWidth > 0) container.style.width = `${pane.clientWidth}px`
        return container.offsetWidth > 0
      }
      if (measurable()) return Promise.resolve(true)
      return new Promise(resolve => {
        let settled = false
        const finish = (ready: boolean) => {
          if (settled) return
          settled = true
          observer.disconnect()
          cancelWidthWait = undefined
          resolve(ready)
        }
        const observer = new ResizeObserver(() => {
          if (cancelled) finish(false)
          else if (measurable()) finish(true)
        })
        cancelWidthWait = () => finish(false)
        observer.observe(container)
        if (pane) observer.observe(pane)
      })
    }

    async function renderMusicSheet() {
      if (!await waitForWidth()) return
      const xml = await musicXmlBlob.text()

      if (cancelled || !containerRef.current) {
        return
      }

      if (!await waitForWidth()) return
      containerRef.current.innerHTML = ''
      containerRef.current.style.width = ''
      let document = reviewDocument(new DOMParser().parseFromString(xml, 'application/xml'), sourceReview ? score : undefined, Boolean(propsRef.current.onSelect) || !score)
      const standaloneScore = !score && !propsRef.current.onSelect ? standaloneTieScore(document) : null
      if (propsRef.current.onSelect && score?.parts?.some(p => p.measures.some(m => m.voices.some(v => v.events.some(e => e.tie_relationship))))) document = correctionTieDocument(document, score)
      const groups = sourceReview ? trustedSourceGroups(score) : xmlSourceGroups(document)
      const pageWidth = groups ? 0 : Number(document.getElementsByTagName('page-width')[0]?.textContent)
      const availableWidth = containerRef.current.closest?.('.review-score-viewport')?.querySelector('.review-score-scroll')?.clientWidth || containerRef.current.clientWidth
      const measures = groups ? [] : Array.from(document.getElementsByTagName('part')[0]?.children ?? []).filter(e => e.localName === 'measure')
      const seedWidth = groups ? sourceEngravingWidth(document, groups) : pageWidth > 0 ? pageWidth : availableWidth || sourceEngravingWidth(document, [measures.map((_, index) => index)])
      setEngravingWidth(seedWidth)
      containerRef.current.style.width = `${seedWidth}px`

      if (!await waitForWidth()) return
      const osmd = new OpenSheetMusicDisplay(
        containerRef.current,
        rendererOptions(Boolean(groups)),
      )

      // A Document also handles valid XML without a declaration; strings can be interpreted as URLs.
      await osmd.load(document)

      if (!await waitForWidth()) return
      if (!cancelled) {
        if (groups) {
          const result = engraveSourceGroups(osmd, groups, (width) => { containerRef.current!.style.width = `${width}px` }, seedWidth)
          setEngravingWidth(result.width)
          setGroupingFailedXml(result.matched ? null : musicXmlBlob)
        } else osmd.render()
        if (standaloneScore) standaloneCleanup = drawStandaloneTies(osmd, standaloneScore)
        osmdRef.current = osmd
        identify(osmd, selectionRef.current)
        bind(osmd)
        refreshMarker()

      }
    }

    renderMusicSheet().catch((error) => {
      if (!cancelled) setFailedXml(musicXmlBlob)
      console.error('Unable to render MusicXML:', error)
    })

    return () => {
      cancelled = true
      cancelWidthWait?.()
      standaloneCleanup?.()
      markerCleanup.current?.(); markerCleanup.current = null
      interactionRef.current?.dispose()
      interactionRef.current = null
      lyricBindings.current?.dispose(); lyricBindings.current = null
      osmdRef.current?.cursor?.hide()
      osmdRef.current = null
    }
  }, [musicXml, sourceReview, score])

  if (!musicXml) {
    return null
  }

  return (
    <div>
      <ReviewScoreViewport title={title} headerActions={headerActions} toolbar={toolbar} sourceReview={true} engravingWidth={engravingWidth}>
        <div ref={containerRef} onClick={choosePosition} className={sourceReview ? 'source-review-page' : undefined} />
      </ReviewScoreViewport>

      {lyricMessage && <p role="status">{lyricMessage}</p>}
      {lyricTarget && lyricScope && <DirectLyricEditor binding={lyricTarget}
        lyric={currentLyric(lyricTarget, lyricScope)} events={score?.parts.flatMap(p => p.measures.flatMap(m => m.voices.flatMap(v => v.events))) ?? []}
        enabled={interactive && !insertionMode && tieTargetIds === null && Boolean(onSelect)}
        close={() => setLyricTarget(null)} selectOwner={id => propsRef.current.onLyricOwnerSelect?.(id)}
        apply={async text => {
          const p = propsRef.current
          if (!lyricBindings.current?.canEdit(lyricTarget) || !p.lyricScope || !currentLyric(lyricTarget, p.lyricScope) || !p.interactive || p.insertionMode || p.tieTargetIds !== null || !p.onLyricApply)
            throw new Error('The lyric or editing mode changed. No edit was sent.')
          const result = await p.onLyricApply(lyricTarget, text)
          const saved = result.lyric
          // Confirm the new rendered ownership and value, rather than treating a successful request as a successful preview.
          const matched = await new Promise<boolean>(resolve => {
            let attempts = 0
            const check = () => {
              const found = lyricBindings.current?.bindings.filter(b => b.reviewId === result.reviewId && b.revision === result.revision && b.lyricId === saved.id && b.eventId === saved.event_id && b.valid() && Boolean(propsRef.current.onSelect)
                && b.renderGeneration > lyricTarget.renderGeneration && b.node.textContent === saved.text)
              if (found?.length === 1) resolve(true)
              else if (++attempts >= 100) resolve(false)
              else setTimeout(check, 50)
            }
            check()
          })
          if (!matched) throw new Error('The canonical lyric was saved, but its visible preview could not be confirmed. Reload review.')
          setLyricMessage('Lyric saved and verified in the Working score.')
        }} />}


      {selection && <p className="review-selection" role="status">Selected: {selection.label}.</p>}
      {failedXml === musicXml && (
        <p role="alert">Unable to preview this MusicXML. Recognition may have produced unsupported notation.</p>
      )}
      {score && <details className="render-details"><summary>Layout details</summary><p role="status">{sourceReview
        ? 'Source review layout: engraving is sized to preserve trusted source systems before Fit/zoom.'
        : 'Fixed engraving layout: Fit and zoom change display scale without reflow.'}</p></details>}
      {groupingFailedXml === musicXml && <p role="status">The renderer could not preserve all trusted source systems within the rendering limit. Compare with the source.</p>}
    </div>
  )
}
