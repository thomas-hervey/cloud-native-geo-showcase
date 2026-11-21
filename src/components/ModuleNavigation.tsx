import Link from 'next/link';
import { FC } from 'react';

interface Module {
  id: string;
  title: string;
  slug: string;
}

interface ModuleNavigationProps {
  modules: Module[];
  currentSlug?: string;
}

const ModuleNavigation: FC<ModuleNavigationProps> = ({ modules, currentSlug }) => {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-md overflow-hidden">
      <div className="bg-blue-600 p-4">
        <h2 className="text-lg font-bold text-white">Modules</h2>
      </div>
      <nav className="p-4">
        <ul className="space-y-2">
          {modules.map((module) => (
            <li key={module.id}>
              <Link
                href={`/cng-modules/${module.slug}`}
                className={`block p-2 rounded hover:bg-gray-100 transition-colors ${currentSlug === module.slug
                    ? 'bg-blue-100 text-blue-800 font-medium'
                    : 'text-gray-700'
                  }`}
              >
                <span className="inline-block w-6 mr-2 text-center">{module.id}</span>
                {module.title}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
};

export default ModuleNavigation;
