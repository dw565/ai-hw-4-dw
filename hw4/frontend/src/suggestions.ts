import type { PageContext } from './api'

/** One-click starter questions for the chat, tuned to the page the shopper is on. */
export function suggestionsFor(page: PageContext): string[] {
  if (page.page_type === 'product') {
    return [
      'Which sizes are in stock?',
      'What colors does this come in?',
      'Show me similar items',
    ]
  }
  if (page.page_type === 'products' && page.results_title) {
    return ['Which of these is cheapest?', 'Which of these are in stock in M?', 'Only ones under $50']
  }
  return ['What hoodies do you have?', 'Gift ideas under $50', 'Tees in stock in XL']
}
