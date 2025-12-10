export interface CoreSignalPayload {
  symbol: string;
  timeframe: string;
  model_name: string;
  direction: string;
  confidence: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  price_momentum: number;
  sentiment_score: number;
  on_chain_score: number;
  alpha_score: number;
}

export interface MemeSignalPayload {
  symbol: string;
  trend_score: number;
  social_score: number;
  momentum: number;
  alpha: number;
  direction: string;
  confidence: number;
}
