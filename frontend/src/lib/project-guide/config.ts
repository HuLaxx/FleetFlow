/**
 * Per-project settings for the project assistant. Everything else under
 * src/lib/project-guide and src/components/assistant is shared verbatim across
 * FleetFlow, GraphGuard and Sentinance.
 */
export const ASSISTANT_CONFIG = {
  homeProject: "fleetflow",
  projectName: "FleetFlow",
  ownerName: "Rahul Khanke",
  contactLine: "email rahulkhanke786@gmail.com or message him at linkedin.com/in/rahulkhanke.",
  theme: "fleetflow",
  launcherLabel: "Ask FleetFlow",
  eyebrow: "Dispatch desk · RAG guide",
  title: "Ask the FleetFlow guide",
  subtitle: "Ask about the project, its stack and evidence, or about Rahul.",
  greeting:
    "Hi! I answer from FleetFlow's own docs and evidence register, and from Rahul's profile. Every answer links to the source it came from.",
  placeholder: "e.g. How does GPS reach the live map?",
  suggestions: [
    "How does FleetFlow plan delivery routes?",
    "What tech stack does FleetFlow use, and what is verified?",
    "How does the Spark, dbt and Airflow lakehouse work?",
    "What is Rahul's experience and background?",
  ],
  /** Routes where the floating launcher would cover task UI. */
  hiddenPaths: ["/driver", "/intro"] as string[],
} as const;
