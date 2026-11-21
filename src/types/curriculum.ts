// TypeScript types for the role-learning curriculum
// Generated from JSON schemas

export type Difficulty = 'intro' | 'intermediate' | 'advanced';
export type Status = 'planned' | 'in_progress' | 'blocked' | 'complete';
export type EffortBucket = 'XS' | 'S' | 'M' | 'L';

export interface Module {
  id: string;
  track: string;
  title: string;
  summary?: string;
  objective: string;
  prerequisites?: string[];
  hours: number;
  effortBuckets?: EffortBucket;
  difficulty: Difficulty;
  status: Status;
  tags?: string[];
  tools: string[];
  datasets?: string[];
  activities?: string[];
  exitCriteria: string[];
  evidence?: string[];
  stretch?: string[];
  dependsOn?: string[];
  version: string;
  reviewedOn?: string;
}

export interface Track {
  id: string;
  title: string;
  status: 'active' | 'planned' | 'deprecated';
  priority: number;
  ownerIntent?: string;
  modules: string[];
  tags?: string[];
  version: string;
}

export interface Tool {
  id: string;
  name: string;
  category: string;
  description: string;
  url?: string;
  integrationDepth: 'none' | 'basic' | 'intermediate' | 'advanced';
  cost: 'free' | 'freemium' | 'paid' | 'enterprise';
  learningCurve: 'low' | 'medium' | 'high';
  tags?: string[];
  version: string;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  format: string;
  size: string;
  source: string;
  license: string;
  updateFrequency: string;
  tags?: string[];
  version: string;
}

export interface CurriculumCatalog {
  modules: Module[];
  tracks: Track[];
  tools: Tool[];
  datasets: Dataset[];
}
