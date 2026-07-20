# ADR-003: Detección de duplicidad multi-señal con exclusión de apps hub

## Estado
Aceptado

## Contexto
Los taskbots reales tienen nombres deliberadamente distintos aunque sean variantes de la misma
utilidad; la duplicidad suele estar **declarada** en un campo ("Similar a TB_X"). Una similitud
puramente textual no los detecta. Además, muchos comparten un sistema **hub** (p.ej. SAP ECC), lo que
con clustering *single-linkage* encadena capacidades distintas en un mega-cluster (problema observado:
un cluster de 10 mezclando proveedores, clientes, productos y pedidos).

## Decisión
Calcular la similitud combinando **tres señales**: (1) **evidencia declarada** de duplicidad (señal
más fuerte), (2) **solapamiento de aplicaciones excluyendo apps hub** (Jaccard), y (3) **similitud
textual** (rapidfuzz). Las apps que aparecen en ≥25% del portafolio se consideran hub y se ignoran en
el solapamiento; una referencia declarada solo fusiona si además comparte una app **no-hub**. El
clustering es **union-find** con umbral configurable.

## Consecuencias
- (+) Detecta duplicidad declarada y no declarada; evita el encadenamiento espurio (cluster máximo bajó
  de 10 a 5, con grupos coherentes).
- (+) Umbral y peso configurables por entorno.
- (−) El corte de "hub" (25%) es heurístico; se documenta y es ajustable. Single-linkage sigue siendo
  transitivo, mitigado por el gate de app no-hub.

## Alternativas consideradas
- **Solo texto (rapidfuzz)**: no detecta variantes con nombres distintos.
- **Restringir a mismo sistema destino (como Parte A)**: válido, pero aquí los bots declaran varios
  sistemas; el gate de "app no-hub" generaliza mejor esa idea.
- **Embeddings semánticos**: mayor costo/dependencia; queda como mejora futura con fallback.
