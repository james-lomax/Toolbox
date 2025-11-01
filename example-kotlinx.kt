package com.citymapper.greenier.ai.llm.gemini

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class GeminiGenerateContentRequest(
    val contents: List<GeminiContent>,
    val generationConfig: GeminiGenerationConfig? = null,
    val tools: List<GeminiTool>? = null,
    val systemInstruction: GeminiSystemInstruction? = null
)
