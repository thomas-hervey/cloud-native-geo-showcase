import fs from 'fs';
import path from 'path';
import { Metadata } from 'next';
import ModuleContent from '@/components/ModuleContent';

export const metadata: Metadata = {
    title: 'Roadmap | Cloud-Native Geospatial Tutorial',
    description: 'The long-term vision, core curriculum, and mastery tracks for this tutorial',
};

export default function RoadmapPage() {
    const filePath = path.join(process.cwd(), 'ROADMAP.md');
    const content = fs.existsSync(filePath)
        ? fs.readFileSync(filePath, 'utf8')
        : '# Roadmap\n\n_Under construction._';

    return (
        <div className="max-w-4xl mx-auto py-8 px-4">
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-8">
                <article className="prose prose-blue max-w-none">
                    <ModuleContent content={content} />
                </article>
            </div>
        </div>
    );
}
