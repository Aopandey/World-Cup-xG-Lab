export type DataConfidence = "Strong" | "Moderate" | "Limited" | "Unavailable";
export type EvidenceLevel = "strong" | "moderate" | "limited" | "unavailable";

export type DateRange = {
  earliest: string | null;
  latest: string | null;
};

export type Team = {
  world_cup_team: string;
  flag_code: string | null;
  flag_image_url?: string | null;
  squad_status: string;
  players_confirmed: number;
  statsbomb_shots: number;
  statsbomb_goals: number;
  total_xg: number;
  goals_minus_xg: number;
  avg_xg_per_shot: number;
  fbref_players_matched: number;
  fbref_coverage_rate: number;
  understat_players_matched?: number;
  understat_coverage_rate?: number;
  data_confidence: DataConfidence;
};

export type TopXgPlayer = {
  player: string;
  shots: number;
  goals: number;
  total_xg: number;
  goals_minus_xg: number;
  avg_xg_per_shot: number;
};

export type RecentFbrefPlayer = {
  player: string;
  position_group?: string | null;
  club?: string | null;
  league?: string | null;
  season?: number | string | null;
  minutes?: number | null;
  goals?: number | null;
  shots?: number | null;
  xg?: number | null;
  xg_per_90?: number | null;
};

export type RecentUnderstatPlayer = {
  player: string;
  position_group?: string | null;
  club?: string | null;
  league?: string | null;
  season?: number | string | null;
  team?: string | null;
  games?: number | null;
  minutes?: number | null;
  goals?: number | null;
  assists?: number | null;
  shots?: number | null;
  xg?: number | null;
  npxg?: number | null;
  xa?: number | null;
  xg_chain?: number | null;
};

export type PositionGroupSummary = {
  position_group: string | null;
  squad_players: number;
  statsbomb_shots: number;
};

export type TeamProfile = {
  world_cup_team: string;
  flag_code: string | null;
  flag_image_url?: string | null;
  statsbomb_shots: number;
  statsbomb_goals: number;
  total_xg: number;
  goals_minus_xg: number;
  avg_xg_per_shot: number;
  statsbomb_date_range: DateRange;
  competitions_included: string[];
  shot_points?: ShotPoint[];
  top_xg_players: TopXgPlayer[];
  top_recent_fbref_players: RecentFbrefPlayer[];
  top_recent_understat_players?: RecentUnderstatPlayer[];
  position_group_summaries: PositionGroupSummary[];
  warnings: string[];
};

export type FbrefRecentRow = {
  season?: number | string | null;
  league?: string | null;
  team?: string | null;
  pos?: string | null;
  minutes?: number | null;
  goals?: number | null;
  assists?: number | null;
  shots?: number | null;
  shots_on_target?: number | null;
  shots_per_90?: number | null;
  xg?: number | null;
  npxg?: number | null;
  xg_per_90?: number | null;
  npxg_per_90?: number | null;
};

export type UnderstatRecentRow = {
  season?: number | string | null;
  league?: string | null;
  team?: string | null;
  position?: string | null;
  games?: number | null;
  minutes?: number | null;
  goals?: number | null;
  assists?: number | null;
  shots?: number | null;
  xg?: number | null;
  npxg?: number | null;
  xa?: number | null;
  key_passes?: number | null;
  xg_chain?: number | null;
  xg_buildup?: number | null;
  yellow?: number | null;
  red?: number | null;
  shot_data_shots?: number | null;
  shot_data_xg?: number | null;
  avg_shot_xg?: number | null;
};

export type UnderstatModelRecentRow = {
  season?: number | string | null;
  league?: string | null;
  team?: string | null;
  understat_model_shots?: number | null;
  understat_model_goals?: number | null;
  understat_model_xg?: number | null;
  understat_source_xg?: number | null;
  understat_model_minus_source_xg?: number | null;
  avg_understat_model_xg?: number | null;
  avg_understat_source_xg?: number | null;
  high_xg_shots?: number | null;
  earliest_match_date?: string | null;
  latest_match_date?: string | null;
};

export type UnderstatModelSummary = {
  shots: number;
  goals: number;
  experimental_xg: number;
  understat_source_xg: number;
  experimental_minus_source_xg: number;
  avg_experimental_xg_per_shot: number;
  avg_understat_source_xg_per_shot: number;
  high_xg_shots: number;
  match_confidence?: string | null;
  matched_player?: string | null;
};

export type DataMbContext = {
  available: boolean;
  source: "DataMB";
  season: "25/26" | string;
  template?: string | null;
  club?: string | null;
  minutes?: number | null;
  percentiles?: Record<string, number>;
  generated_radar_path?: string | null;
  source_url?: string | null;
  notes?: string | null;
  reason?: string | null;
  match_status?: string | null;
  match_confidence?: string | null;
};

export type PlayerProfile = {
  player: string;
  player_normalized: string;
  world_cup_team: string;
  position: string | null;
  position_group: string | null;
  club: string | null;
  league: string | null;
  squad_status: string | null;
  statsbomb_shots: number;
  statsbomb_goals: number;
  total_xg: number;
  goals_minus_xg: number;
  avg_xg_per_shot: number;
  statsbomb_date_range: DateRange;
  shot_points?: ShotPoint[];
  fbref_available: boolean;
  fbref_recent_rows: FbrefRecentRow[];
  understat_available?: boolean;
  understat_recent_rows?: UnderstatRecentRow[];
  understat_model_available?: boolean;
  understat_model_recent_rows?: UnderstatModelRecentRow[];
  understat_model_summary?: UnderstatModelSummary | null;
  datamb_25_26?: DataMbContext;
  data_confidence: DataConfidence;
  imageUrl: string | null;
  avatarSeed: string;
  warnings: string[];
};

export type SquadPlayer = {
  world_cup_team: string;
  player: string;
  player_normalized?: string;
  position: string | null;
  position_group: string | null;
  club: string | null;
  league: string | null;
  squad_status: string | null;
  data_source?: string | null;
  imageUrl?: string | null;
  avatarSeed?: string;
};

export type SquadResponse = {
  world_cup_team: string;
  players: SquadPlayer[];
  count: number;
};

export type PlayersResponse = {
  count: number;
  players: PlayerProfile[];
};

export type ModelMetric = {
  model_name: string;
  prediction_file?: string;
  model_label?: string;
  training_source?: string;
  test_source?: string;
  feature_set?: string;
  rows?: number;
  train_rows?: number;
  test_rows?: number;
  feature_count?: number;
  dataset_name?: string;
  evaluation_scope?: string;
  actual_feature_count?: number;
  reference_features_available?: number;
  reference_features_missing_pct?: number;
  description?: string;
  log_loss: number;
  brier_score: number;
  roc_auc: number;
  accuracy_at_0_5: number;
};

export type ModelSummary = {
  experiment_name: string;
  best_model_by_log_loss: string | null;
  best_research_model_by_log_loss?: string | null;
  models: ModelMetric[];
  production_models?: ModelMetric[];
  research_source_models?: ModelMetric[];
  feature_missingness_experiments?: ModelMetric[];
  research_explanation?: string;
  xg_explanation: string;
  limitations: string[];
};

export type DataCoverage = {
  total_world_cup_teams: number;
  teams_with_squad_data: number;
  teams_missing_squad_data: string[];
  teams_with_statsbomb_data: number;
  missing_teams: string[];
  total_squad_players: number;
  fbref_matched_players: number;
  fbref_missing_players: number;
  fbref_coverage_rate: number;
  understat_matched_players?: number;
  understat_missing_players?: number;
  understat_coverage_rate?: number;
  datamb_matched_players?: number;
  datamb_missing_players?: number;
  datamb_coverage_rate?: number;
  date_range: DateRange;
  known_limitations: string[];
};

export type SearchResponse = {
  query: string;
  teams: Team[];
  players: PlayerProfile[];
  team_count: number;
  player_count: number;
};

export type PlayerFilters = {
  team?: string;
  position_group?: string;
  data_confidence?: DataConfidence | string;
};

export type ShotPoint = {
  shot_x?: number | null;
  shot_y?: number | null;
  predicted_xg?: number | null;
  actual_goal?: boolean | null;
};
