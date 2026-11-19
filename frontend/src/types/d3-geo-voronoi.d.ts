// d3-geo-voronoi não publica tipos — declaração mínima com só o que usamos
// (diagrama de Voronoi esférico exato a partir de pontos lon/lat, sem grade).
declare module 'd3-geo-voronoi' {
  interface GeoVoronoi<T> {
    x(accessor: (d: T) => number): GeoVoronoi<T>
    y(accessor: (d: T) => number): GeoVoronoi<T>
    polygons(data?: T[]): GeoJSON.FeatureCollection<GeoJSON.Polygon, { site: T; sitecoordinates: [number, number] }>
  }
  export function geoVoronoi<T = unknown>(data?: T[]): GeoVoronoi<T>
}
