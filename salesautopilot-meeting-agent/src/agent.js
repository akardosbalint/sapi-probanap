const Anthropic = require('@anthropic-ai/sdk');
const { SYSTEM_PROMPT } = require('./systemPrompt');

class SalesAutopilotAgent {
  constructor() {
    this.client = new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY,
    });
    this.model = 'claude-opus-4-8';
    this.conversationHistory = [];
  }

  async analyzeTranscript(transcript) {
    const userMessage = `Az alábbi meeting transcript-et kell elemezned:\n\n${transcript}`;

    this.conversationHistory.push({
      role: 'user',
      content: userMessage,
    });

    const response = await this.client.messages.create({
      model: this.model,
      max_tokens: 4096,
      system: SYSTEM_PROMPT,
      messages: this.conversationHistory,
    });

    const assistantMessage = response.content[0].text;

    this.conversationHistory.push({
      role: 'assistant',
      content: assistantMessage,
    });

    return {
      analysis: assistantMessage,
      usage: response.usage,
      stopReason: response.stop_reason,
    };
  }

  async followUp(question) {
    if (this.conversationHistory.length === 0) {
      throw new Error('Nincs előző elemzés. Először futtasd az analyzeTranscript metódust.');
    }

    this.conversationHistory.push({
      role: 'user',
      content: question,
    });

    const response = await this.client.messages.create({
      model: this.model,
      max_tokens: 2048,
      system: SYSTEM_PROMPT,
      messages: this.conversationHistory,
    });

    const assistantMessage = response.content[0].text;

    this.conversationHistory.push({
      role: 'assistant',
      content: assistantMessage,
    });

    return {
      answer: assistantMessage,
      usage: response.usage,
    };
  }

  resetConversation() {
    this.conversationHistory = [];
  }

  getHistory() {
    return this.conversationHistory;
  }
}

module.exports = { SalesAutopilotAgent };
