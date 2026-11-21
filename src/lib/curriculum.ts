import fs from 'fs';
import path from 'path';

export interface BaseModuleMetadata {
  title: string;
  description: string;
  status: 'complete' | 'in_progress' | 'planned' | 'blocked';
  track: string;
  reviewNeeded?: boolean;
  reviewNote?: string;
  exerciseFolder?: string;
}

/**
 * Metadata specifically for Cloud-Native Geospatial (CNG) technology modules.
 */
export type ModuleType = 'tutorial' | 'reference' | 'prototype' | 'capstone';

export interface CNGModuleMetadata extends BaseModuleMetadata {
  type: ModuleType;
  techniques: string[];
  tools: string[];
}

/**
 * Metadata for the legacy PM curriculum tracker.
 */
export interface PMModuleMetadata extends BaseModuleMetadata {
  summary?: string;
  objective?: string;
  hours?: number;
  difficulty?: string;
  version?: string;
  tags?: string[];
  effortBuckets?: string;
  prerequisites?: string[];
  activities?: string[];
  exitCriteria?: string[];
  datasets?: string[];
  stretch?: string[];
  dependsOn?: string[];
  reviewedOn?: string;
  evidence?: string[];
  // Compatibility for older fields if they existed in PM tracks
  stacks?: string[];
  techniques?: string[];
  tools?: string[];
}

export type ModuleMetadata = CNGModuleMetadata | PMModuleMetadata;

export interface Track {
  id: string;
  title: string;
  description: string;
  modules: string[]; // List of slugs
  // Legacy PM Tracker Compatibility
  status?: 'active' | 'planned' | 'deprecated';
  priority?: number;
  ownerIntent?: string;
  version?: string;
  tags?: string[];
}

export interface Stack {
  id: string;
  title: string;
  description: string;
  modules: string[]; // List of slugs
}

export interface Curriculum {
  tracks: Track[];
  stacks: Stack[];
  modules: Record<string, ModuleMetadata>;
}

let cachedCurriculum: Curriculum | null = null;

export function getCurriculum(): Curriculum {
  if (cachedCurriculum) return cachedCurriculum;

  const configPath = path.join(process.cwd(), 'src/content/curriculum.json');
  if (!fs.existsSync(configPath)) {
    throw new Error('curriculum.json not found');
  }

  const raw = fs.readFileSync(configPath, 'utf8');
  cachedCurriculum = JSON.parse(raw);
  return cachedCurriculum as Curriculum;
}

export function getAllModules() {
  const curriculum = getCurriculum();
  // Return modules in order of tracks
  const orderedSlugs = curriculum.tracks.flatMap(t => t.modules);
  return orderedSlugs.map(slug => ({
    slug,
    ...curriculum.modules[slug]
  }));
}

import matter from 'gray-matter';

export function getModule(slug: string) {
  const curriculum = getCurriculum();
  const meta = curriculum.modules[slug];
  if (!meta) return null;

  const moduleDir = path.join(process.cwd(), 'src/content/cng-modules');
  const filePath = path.join(moduleDir, `${slug}.md`);
  
  if (!fs.existsSync(filePath)) return null;
  
  const fileContent = fs.readFileSync(filePath, 'utf8');
  const { content } = matter(fileContent);

  return {
    slug,
    metadata: meta,
    content
  };
}

export function getAdjacentModules(slug: string) {
  const curriculum = getCurriculum();
  const orderedSlugs = curriculum.tracks.flatMap(t => t.modules);
  const index = orderedSlugs.indexOf(slug);

  return {
    prev: index > 0 ? { slug: orderedSlugs[index - 1], ...curriculum.modules[orderedSlugs[index - 1]] } : null,
    next: index < orderedSlugs.length - 1 ? { slug: orderedSlugs[index + 1], ...curriculum.modules[orderedSlugs[index + 1]] } : null
  };
}
