# ADR-011: Multi-LLM Tool Compatibility — Schema Flattening y Param Tolerance

**Estado:** Aceptada
**Autor:** SaludAI
**Fecha:** 2026-03-22
**Sprint:** 6 (Launch)

## Contexto

Al expandir el benchmark a modelos no-Anthropic (GPT-4o, Llama 3.3, Qwen 3.5), descubrimos que **GPT-4o no genera el campo `params` en tool calls** para queries filtradas simples.

### El problema concreto

Nuestras tools FHIR (`count_fhir`, `search_fhir`) usan un patrón estándar de Anthropic:

```json
{
  "properties": {
    "resource_type": {"type": "string"},
    "params": {
      "type": "object",
      "additionalProperties": {"type": "string"},
      "description": "Parámetros de búsqueda FHIR..."
    }
  },
  "required": ["resource_type"]
}
```

- **Claude Sonnet:** genera `{"resource_type": "Patient", "params": {"gender": "male"}}` ✅
- **Llama 3.3 70B:** genera `{"resource_type": "Patient", "params": {"gender": "male"}}` ✅
- **Qwen 3.5 9B:** genera `{"resource_type": "Patient", "params": {"gender": "male"}}` ✅
- **GPT-4o:** genera `{"resource_type": "Patient"}` ❌ (omite `params` completamente)

GPT-4o **sí puede** generar keys a top-level (para Medium/Complex con `_has` a veces lo hacía), pero nunca genera el objeto `params` nested para filtros demográficos simples (gender, address-state, birthdate). El resultado: 7/15 Simple incorrectas, todas retornando "200 pacientes" sin filtrar.

### Root cause analysis

El comportamiento es consistente con una limitación conocida de OpenAI function calling:

1. **`additionalProperties` en objetos nested** es pobremente soportado por GPT-4o. El modelo no "entiende" que puede poner cualquier key dentro de un objeto abierto.
2. **`strict: true`** de OpenAI (Structured Outputs) directamente prohíbe `additionalProperties: true`, confirmando que no es un patrón bien soportado en su stack.
3. El campo `params` es **optional** (`required` solo incluye `resource_type`), lo que le da al modelo "permiso" para omitirlo.
4. A top-level, con `additionalProperties` en el schema raíz, GPT-4o sí genera keys adicionales consistentemente.

### Magnitud del impacto

Sin fix, GPT-4o obtenía **43.5% accuracy** en las primeras 23 preguntas (15S + 8M). Con los fixes: **~96% en las mismas 23** (16 correctas originales + 7 recuperadas).

## Decisión

Implementamos un **patrón de compatibilidad multi-LLM en dos capas** que no modifica las definiciones de tools ni el prompt de Anthropic:

### Capa 1: Schema Flattening para OpenAI (`_flatten_params_for_openai`)

En `llm.py`, la función `_tools_to_openai()` transforma el schema antes de enviarlo a la API de OpenAI:

```python
# Antes (lo que Anthropic recibe, sin cambios):
{"properties": {"resource_type": ..., "params": {"additionalProperties": ...}}}

# Después (lo que GPT-4o recibe):
{"properties": {"resource_type": ...}, "additionalProperties": {"type": "string"}}
```

La transformación:
1. Detecta tools con un campo `params` que tenga `additionalProperties`
2. Remueve `params` del schema
3. Promueve `additionalProperties` al nivel raíz del schema

**IMPORTANTE: el flattening es condicional.** Solo se aplica cuando `base_url is None`
(OpenAI nativo). Para Together AI y Ollama (`base_url` presente), el schema se envía
sin cambios. Razón: Qwen 3.5 9B con schema aplanado cae de 29% a 13% (respuestas
vacías en 82/86 casos — el modelo se confunde con `additionalProperties` a nivel raíz).

```python
# En OpenAILLMClient.generate():
flatten = self._base_url is None  # True solo para OpenAI nativo
kwargs["tools"] = _tools_to_openai(tools, flatten=flatten)
```

### Capa 2: Param Tolerance en el executor (`_merge_params`)

En `tools.py`, una función que reconcilia ambos formatos en el momento de ejecución:

```python
def _merge_params(arguments: dict[str, Any]) -> dict[str, str]:
    params = dict(arguments.get("params") or {})
    # Qwen gotcha: unwrap additionalProperties if sent as a field
    additional = arguments.get("additionalProperties")
    if isinstance(additional, dict):
        for k, v in additional.items():
            params.setdefault(k, str(v))
    elif isinstance(additional, str) and "=" in additional:
        k, _, v = additional.partition("=")
        params.setdefault(k.strip(), v.strip())
    for key, value in arguments.items():
        if key not in {"resource_type", "params", "additionalProperties"}:
            params.setdefault(key, str(value))
    return params
```

Normaliza **tres** comportamientos distintos:

| LLM | Comportamiento | Ejemplo |
|-----|---------------|---------|
| Anthropic/Llama | params en `params` | `{"resource_type": "Patient", "params": {"gender": "male"}}` |
| GPT-4o | params a top-level | `{"resource_type": "Patient", "gender": "male"}` |
| Qwen (schema leak) | params en `additionalProperties` | `{"resource_type": "Patient", "additionalProperties": {"birthdate": "le1964"}}` |

Precedencia: `params` > `additionalProperties` > top-level (`setdefault` semántica).

### Complementos adicionales

- **Retry con exponential backoff** en ambos LLM clients (429, 503, 529). 4 retries, backoff 1→2→4→8s. Eliminó todos los errores de rate limiting.
- **`suggested_query` en el planner**: el QueryPlan ahora incluye una query concreta sugerida (e.g., `count_fhir('Patient', {'gender': 'male'})`). Se inyecta en el system prompt del executor. Ayuda a todos los modelos, no solo GPT-4o.

## Consecuencias

### Positivas

- **Zero-change para Anthropic:** las tool definitions, el prompt, y el schema que Claude recibe son idénticos. No hay riesgo de regresión en el benchmark principal.
- **GPT-4o pasa de ~53% a 100% en Simple.** El problema central de tool calling está resuelto.
- **Extensible:** cualquier futuro proveedor OpenAI-compatible (Mistral, etc.) se beneficia automáticamente.
- **El patrón es invisible:** no hay `if provider == "openai"` en el agent loop ni en las tools. La adaptación ocurre en la capa de serialización (llm.py) y deserialización (tools.py).

### Negativas

- **Dos representaciones del mismo schema** coexisten. Hay que recordar que el schema Anthropic y el schema OpenAI son distintos para las mismas tools.
- **`_merge_params` amplía la superficie de aceptación**: acepta params donde el schema original no los esperaría. Es deliberado pero reduce la validación estricta.

### Riesgos

- Si Anthropic cambia su formato de tool calling, o si OpenAI mejora su soporte de `additionalProperties`, estos adaptadores podrían volverse innecesarios. Son fáciles de remover.
- El planner genera `suggested_query` con Haiku — si Haiku cambia de comportamiento, podría generar queries incorrectas. Pero el executor no está obligado a seguirlas.

## Lección aprendida: Schema Leak en Qwen

### El incidente

Al implementar el schema flattening, `_flatten_params_for_openai` promueve
`additionalProperties` al nivel raíz del schema JSON. GPT-4o lo interpreta
correctamente como directiva de JSON Schema. Pero **Qwen 3.5 9B lo interpreta
como un campo llamado `additionalProperties`** y genera:

```json
{"resource_type": "Patient", "additionalProperties": {"birthdate": "le1964-01-01"}}
```

### Root cause

Los modelos pequeños (9B params) no tienen una distinción robusta entre JSON Schema
*keywords* (`additionalProperties`, `type`, `required`) y campos de datos del usuario.
Ven `additionalProperties` como "otro campo que puedo llenar".

### El fix

En vez de hacer el flattening condicional por provider (frágil, acopla lógica de negocio
al transporte), normalizamos en `_merge_params`: si aparece `additionalProperties` como
key en los arguments, desempaquetamos su contenido al dict de params.

### Regla derivada

> **Cualquier cambio en tool definitions, schema, o prompt debe validarse contra TODOS
> los modelos del benchmark antes de considerar la tarea completa.** Un fix para un modelo
> puede romper otro. La capa de normalización (`_merge_params`) es el lugar seguro para
> absorber diferencias — no el schema ni el prompt.

## Alternativas consideradas

### Opción A: Mejorar tool descriptions con más ejemplos

- **Probada:** agregamos ejemplos explícitos de `gender`, `address-state`, `birthdate` en la descripción de `count_fhir`.
- **Resultado:** 0/7 mejora. GPT-4o ignora la descripción de `params` si el schema no lo fuerza a generarlo.
- **Descartada:** el problema es de schema, no de documentación.

### Opción B: Inyectar `suggested_query` en system prompt (sin schema change)

- **Probada:** el planner genera `count_fhir('Patient', {'gender': 'male'})` y se inyecta como "Query sugerida" en el prompt.
- **Resultado:** 2/7 mejora (inconsistente). GPT-4o a veces sigue la sugerencia, a veces no.
- **Adoptada parcialmente:** la `suggested_query` se mantuvo como complemento, pero no resuelve el problema solo.

### Opción C: Propiedades explícitas por filtro (gender, address-state, etc.)

- Agregar `gender`, `address-state`, `birthdate` como propiedades nombradas en el schema.
- **Descartada:** acopla conocimiento FHIR específico al schema de las tools. No escala con nuevos resource types o search params.

### Opción D: `strict: true` de OpenAI (Structured Outputs)

- Fuerza al modelo a seguir el schema exactamente.
- **Incompatible:** `strict: true` prohíbe `additionalProperties: true`, que es exactamente lo que necesitamos para search params dinámicos.

### Opción E: Prompt engineering agresivo ("NUNCA llamar sin params")

- **Descartada:** contamina el prompt para todos los modelos, frágil, y contradice el principio de que las tools se auto-documentan.

## Marco teórico

### Tool Calling como API Design

El patrón `params: {additionalProperties: string}` es el equivalente en LLM tool calling de `**kwargs` en Python o `Record<string, string>` en TypeScript. Es un "escape hatch" para APIs con parámetros dinámicos.

Este patrón funciona bien cuando el modelo tiene experiencia previa con la API (Claude conoce FHIR search params por training). Funciona mal cuando el modelo trata el schema como una especificación rígida (GPT-4o interpreta "optional object with open keys" como "probablemente no necesito llenarlo").

### Analogía con Adapter Pattern (GoF)

La solución sigue el **Adapter Pattern**: la interfaz interna (tool definitions con `params`) se mantiene canónica, y un adaptador por proveedor (`_flatten_params_for_openai`) traduce a la representación que cada modelo entiende mejor. El `_merge_params` actúa como un **normalizer** que unifica las distintas representaciones de vuelta al formato interno.

### Provider-Specific Schema Optimization

Es análogo a cómo los ORMs generan SQL distinto para PostgreSQL vs MySQL vs SQLite: mismo modelo conceptual, distinta representación según las capacidades del backend. En LLM tool calling, cada modelo tiene fortalezas y debilidades en cómo interpreta JSON Schema.

## Referencias

- OpenAI Structured Outputs: `strict: true` prohíbe `additionalProperties` — [OpenAI docs](https://platform.openai.com/docs/guides/structured-outputs)
- Anthropic tool use: soporta `additionalProperties` nativamente — [Anthropic docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- FHIR Search params son dinámicos por diseño — cada resource type tiene su propio set
- GoF Adapter Pattern: convierte la interfaz de una clase en otra que el cliente espera
