# ADR-0004 · Inferencia: motor único llama.cpp/MLX de Jan

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Contexto
El presupuesto es de 32 GB como máximo. Duplicar motores (uno en la UI y otro en el backend) duplicaría los modelos en RAM.

## Decisión
- Valkiria Core consume el servidor compatible con OpenAI de Jan (`127.0.0.1:1337`, API key en el llavero). No embebe su propio motor.
- Backends de aceleración: Metal o MLX (macOS), CUDA o Vulkan (Windows con GPU) y CPU con AVX2.
- Salidas estructuradas con JSON schema o gramáticas de llama.cpp para el router y las herramientas.
- Política de memoria: **un solo modelo generativo grande** cargado; el modelo de visión o de voz desplaza temporalmente al principal.

## Consecuencias
- (+) Un solo modelo en memoria y aceleración por plataforma resuelta por Jan.
- (−) Acoplamiento al contrato HTTP de Jan; se mitiga con el puerto `ChatModelPort`. En modo equipo se usa vLLM con el mismo puerto.
