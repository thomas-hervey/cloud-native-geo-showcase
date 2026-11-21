import type { Metadata } from 'next';
import type { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'Where do LLMs think neighborhoods are? | Spatial Eval',
  description:
    'Compares where LLMs place San Francisco neighborhoods with official SF Planning boundaries, alongside how much reference sources (OSM, Zillow, Click That Hood) disagree with each other.',
};

export default function SpatialEvalLayout({ children }: { children: ReactNode }) {
  return children;
}
