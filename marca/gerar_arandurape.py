# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Gera arandurape-logo.svg e arandurape-simbolo.svg (globo ortográfico com o sul para cima, Natural Earth 1:110m; texto em
contorno, Lato Semibold). Uso: python gerar_arandurape.py [naturalearth_lowres.shp]. Precisa de numpy, geopandas, shapely e fontTools,
fora das dependências do projeto."""
import math, sys
from pathlib import Path
import numpy as np
import geopandas as gpd
from shapely.ops import unary_union
from shapely.geometry import Polygon
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

# Natural Earth 1:110m admin-0 countries, geographic coordinates.
source = sys.argv[1] if len(sys.argv)>1 else '/opt/pyvenv/lib/python3.13/site-packages/pyogrio/tests/fixtures/naturalearth_lowres/naturalearth_lowres.shp'
gdf=gpd.read_file(source)
lon0,lat0=np.radians([-53,-14]); R=340; cx=cy=400
# Rotate the orthographic projection by 180 degrees: south up, east left.
def xyz(lon,lat):
    l,p=np.radians([lon,lat]); d=l-lon0
    return np.array([math.cos(p)*math.sin(d),math.cos(lat0)*math.sin(p)-math.sin(lat0)*math.cos(p)*math.cos(d),math.sin(lat0)*math.sin(p)+math.cos(lat0)*math.cos(p)*math.cos(d)])
def xy(v): return (cx-R*v[0],cy+R*v[1])
def fmt(p): return f'{p[0]:.2f},{p[1]:.2f}'
def points(coords):
    res=[]
    for a,b in zip(coords[:-1],coords[1:]):
        l1,p1=a[:2]; l2,p2=b[:2]; dl=l2-l1
        if abs(dl)>180: dl-=math.copysign(360,dl)
        n=max(1,math.ceil(max(abs(dl),abs(p2-p1))/0.5))
        for t in np.arange(n)/n: res.append(xyz(l1+t*dl,p1+t*(p2-p1)))
    res.append(xyz(*coords[-1][:2])); return res

def crossing(a,b):
    c=a+(b-a)*(-a[2]/(b[2]-a[2])); return c/np.linalg.norm(c)
def visible_runs(vs):
    runs=[]; cur=[]
    if vs[0][2]>=0: cur=[vs[0]]
    for a,b in zip(vs[:-1],vs[1:]):
        if a[2]>=0 and b[2]>=0: cur.append(b)
        elif a[2]>=0: cur.append(crossing(a,b)); runs.append(cur); cur=[]
        elif b[2]>=0: cur=[crossing(a,b),b]
    if cur: runs.append(cur)
    return runs

def line(vs): return ' '.join('M'+' L'.join(fmt(xy(v)) for v in run) for run in visible_runs(vs) if len(run)>1)
def ring(coords):
    vs=points(list(coords)); runs=visible_runs(vs)
    if not runs: return ''
    if vs[0][2]>=0 and len(runs)>1: runs=[runs[-1]+runs[0][1:]]+runs[1:-1]
    if len(runs)==1 and all(v[2]>=0 for v in vs): return 'M'+' L'.join(fmt(xy(v)) for v in runs[0])+' Z'
    # Close clipped coastline runs on the globe limb using the short arc.
    out=[]
    for run in runs:
        if len(run)<2: continue
        a,b=xy(run[-1]),xy(run[0]); t1=math.atan2(a[1]-cy,a[0]-cx); t2=math.atan2(b[1]-cy,b[0]-cx)
        delta=(t2-t1+math.pi)%(2*math.pi)-math.pi
        out.append('M'+' L'.join(fmt(xy(v)) for v in run)+f' A{R},{R} 0 0 {int(delta>0)} {fmt(b)} Z')
    return ' '.join(out)
def geom(g):
    if g.geom_type=='Polygon': return ' '.join([ring(g.exterior.coords)]+[ring(i.coords) for i in g.interiors])
    return ' '.join(geom(p) for p in g.geoms if p.geom_type in ('Polygon','MultiPolygon'))

def path(d,fill='none',stroke='none',sw=1): return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round" fill-rule="evenodd"/>'
blue='#084B54'; green='#16834A'; gray='#BCC8D0'; gold='#E9A318'; grid='#91AAB3'
parts=[]
parts.append(f'<circle cx="400" cy="400" r="340" fill="#FFFFFF"/>')
parts.append('<g clip-path="url(#globe)">')
for lon in range(-180,180,30): parts.append(path(line([xyz(lon,p) for p in np.linspace(-90,90,361)]),stroke=grid,sw=2.6))
for lat in range(-60,90,30): parts.append(path(line([xyz(l,lat) for l in np.linspace(-180,180,721)]),stroke=grid,sw=2.6))
# Country polygons individually avoid the antimeridian complications of a global dissolve.
for _,row in gdf.iterrows():
    if row['name']!='Brazil': parts.append(path(geom(row.geometry),gray))
brazil=gdf[gdf.name=='Brazil'].geometry.iloc[0]; parts.append(path(geom(brazil),green, '#FFFFFF',2))
# A stylized, non-geographic route with a hub at the projection center.
route='M 72,565 C 110,478 260,449 400,400 S 693,302 706,193'
parts.append(path(route,stroke='#FFFFFF',sw=14)); parts.append(path(route,stroke=gold,sw=9))
parts.append('<circle cx="400" cy="400" r="16" fill="'+gold+'" stroke="white" stroke-width="5"/>')
parts.append('</g>'); parts.append(f'<circle cx="400" cy="400" r="340" fill="none" stroke="{blue}" stroke-width="13"/>')
# Outline text, no font dependency in the delivered SVG.
font=TTFont('/usr/share/fonts/truetype/lato/Lato-Semibold.ttf'); glyphs=font.getGlyphSet(); cmap=font.getBestCmap(); units=font['head'].unitsPerEm
word='Arandurapé'; widths=[font['hmtx'][cmap[ord(c)]][0] for c in word]; scale=675/sum(widths); x=(800-sum(widths)*scale)/2; txt=[]
for c,w in zip(word,widths):
    pen=SVGPathPen(glyphs); glyphs[cmap[ord(c)]].draw(TransformPen(pen,(scale,0,0,-scale,x,860))); txt.append(path(pen.getCommands(),blue)); x+=w*scale

def save(name,body,h):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 {h}" role="img" aria-label="Arandurap&#233;">\n<title>Arandurap&#233;</title><desc>South-up orthographic globe centered at 14 S, 53 W. Natural Earth 1:110m. Gold route is symbolic.</desc><defs><clipPath id="globe"><circle cx="400" cy="400" r="340"/></clipPath></defs>\n'+ '\n'.join(body)+'\n</svg>'
    Path(__file__).with_name(name).write_text(svg)
save('arandurape-logo.svg',parts+txt,900); save('arandurape-simbolo.svg',parts,800)
