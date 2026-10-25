import { expect,it } from 'vitest';
import { anchorAt,dragPitch,ledgerLines,point,fitScale,isStaffInsertionArea,measureBox,systemFor } from '../src/notation';
import { clone,demo } from '../src/model';
it('treble lines and spaces use diatonic positions, not semitone spacing',()=>{expect([64,65,67,69,71,72,74,76,77].map(p=>point([0,1],p).y)).toEqual([200,195,190,185,180,175,170,165,160]);});
it('two separate four-beat measures share each system',()=>{expect([0,1,2,3,4].map(b=>point([b,1],67).x)).toEqual([170,245.625,321.25,396.875,512.5]);expect(point([4,1],67).y).toBe(point([0,1],67).y);expect(point([8,1],67).y-point([0,1],67).y).toBe(245);expect(measureBox(0)).toEqual({start:150,end:492.5,top:160,bottom:200});expect(measureBox(1).end).toBe(835);});
it('middle C has a ledger line, D4 has none; high notes use ledger lines',()=>{expect(ledgerLines([0,1],60)).toEqual([210]);expect(ledgerLines([0,1],62)).toEqual([]);expect(ledgerLines([0,1],81)).toEqual([150]);});
it('pointer anchor and pitch drag use the same staff geometry',()=>{expect(anchorAt(point([2,1],67).x,190)).toEqual({onset:[4,2],pitch:67});expect(dragPitch(67,-20)).toBe(74);});
it('render geometry does not alter musical data or create rests for missing beats',()=>{const d=demo(),before=clone(d);for(const e of d.events)for(const h of e.heads){point(e.onset,h.pitch);ledgerLines(e.onset,h.pitch);}expect(d).toEqual(before);expect(d.events.some(e=>e.rest)).toBe(false);});

it('Fit fills pane width and allows vertical scrolling',()=>{const z=fitScale(500,350);expect(900*z).toBeLessThanOrEqual(500);expect(900*z).toBeCloseTo(500);expect(650*z).toBeGreaterThan(350);expect(fitScale(500,350)).toBe(fitScale(500,350));});

it('lyric/text whitespace is not an insertion target',()=>{expect(isStaffInsertionArea(190)).toBe(true);expect(isStaffInsertionArea(435)).toBe(true);expect(isStaffInsertionArea(262)).toBe(false);expect(isStaffInsertionArea(320)).toBe(false);});

it('event anchors stay inside their own numbered measure including fractions',()=>{for(const onset of [[0,1],[2,3],[3,1],[4,1],[23,3],[8,1]] as [number,number][]){const box=measureBox(Math.floor(onset[0]/onset[1]/4)),p=point(onset,67);expect(p.x).toBeGreaterThan(box.start);expect(p.x).toBeLessThan(box.end);expect(systemFor(onset)).toBe(Math.floor(onset[0]/onset[1]/8));expect(p.y).toBe(190+Math.floor(onset[0]/onset[1]/8)*245);}});
