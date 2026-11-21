import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

const authEnabled = process.env.NEXT_PUBLIC_FEATURE_AUTH_ENABLED !== "false";

const ALL_SECTIONS = [
  {
    href: "/cng-modules",
    label: "Cloud-Native Geospatial",
    description:
      "Technical track-based tutorials on cloud-native fundamentals, performance & product patterns, advanced analysis & visualization, geoAI, geo agents, Earth observation, and more",
    color: "border-blue-200 hover:border-blue-400",
    badgeColor: "bg-blue-500",
    public: true,
  },
  {
    href: "/scout/lab",
    label: "Scout Lab",
    description:
      "Interactive geospatial query lab — explore Overture Maps data with natural language.",
    color: "border-indigo-200 hover:border-indigo-400",
    badgeColor: "bg-indigo-600",
    public: true,
  },
  {
    href: "/spatial-eval",
    label: "Spatial Eval",
    description:
      "Benchmark and evaluate how well LLMs understand geographic knowledge.",
    color: "border-teal-200 hover:border-teal-400",
    badgeColor: "bg-teal-600",
    public: true,
  },
  {
    href: "/resources",
    label: "Resources",
    description: "Curated reference links, dataset sources, and tooling guides.",
    color: "border-yellow-200 hover:border-yellow-400",
    badgeColor: "bg-yellow-500",
    public: false,
  },
  {
    href: "/roadmap",
    label: "Roadmap",
    description: "Upcoming modules, planned exercises, and learning milestones.",
    color: "border-purple-200 hover:border-purple-400",
    badgeColor: "bg-purple-500",
    public: true,
  },
];

export default async function Home() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const isAuthenticated = !authEnabled || !!user;

  const visibleSections = ALL_SECTIONS.filter(
    (s) => isAuthenticated || s.public
  );

  return (
    <main className="flex min-h-screen flex-col items-center justify-start p-8 bg-gray-50">
      <div className="w-full max-w-5xl mx-auto">
        {/* Hero */}
        <div className="text-center py-12 md:py-20">
          <h1 className="text-4xl md:text-6xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-700 to-orange-500">
            Thomas&apos;s Learning Hub
          </h1>
          <p className="text-lg md:text-xl text-gray-600 max-w-2xl mx-auto mb-10">
            A self-paced platform for cloud-native geospatial engineering, spatial AI, and product strategy.
          </p>
          {!isAuthenticated && authEnabled && (
            <p className="text-sm text-gray-400 mb-2">
              To explore more resources, reach out to me.
            </p>
          )}
        </div>

        {/* Section grid */}
        <div className="grid md:grid-cols-2 gap-6">
          {visibleSections.map((section) => (
            <Link
              key={section.href}
              href={section.href}
              className={`bg-white p-8 rounded-xl shadow-sm border-2 ${section.color} transition-all hover:shadow-md`}
            >
              <div className="flex items-center gap-3 mb-3">
                <span className={`inline-block w-2.5 h-2.5 rounded-full ${section.badgeColor}`} />
                <h2 className="text-xl font-bold text-gray-900">{section.label}</h2>
              </div>
              <p className="text-gray-600 text-sm leading-relaxed">{section.description}</p>
            </Link>
          ))}
        </div>

        {/* About */}
        <div className="bg-white border border-gray-100 p-8 rounded-xl mt-16 shadow-sm">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">About This Project</h2>
          <p className="text-gray-700 mb-3">
            This hub is a personal learning platform for cloud-native geospatial technologies. Each module covers a
            specific layer of the modern spatial data stack — from file formats and object storage, to LLM-powered
            spatial reasoning and production pipeline design.
          </p>
          <p className="text-gray-700">
            Content is inspired by presentations from the Cloud Native Geospatial Conference and hands-on experimentation
            with tools like STAC, COG, Zarr, GeoParquet, Apache Iceberg, and DuckDB.
          </p>
        </div>
      </div>
    </main>
  );
}
