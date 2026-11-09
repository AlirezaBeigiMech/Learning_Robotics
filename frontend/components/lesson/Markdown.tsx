"use client";

import yaml from "js-yaml";
import { memo, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { PubSubDiagram } from "../widgets/PubSubDiagram";
import { Callout, QosMatrix } from "../widgets/Widgets";
import { TransformPlayground } from "../widgets/TransformPlayground";

const WIDGETS: Record<string, (p: { config: any }) => React.ReactNode> = {
  "pubsub-diagram": PubSubDiagram,
  "qos-matrix": QosMatrix,
  callout: Callout,
  "transform-playground": TransformPlayground,
};

// Renderers are defined ONCE at module level. Inline component functions would get a new identity on every
// render, making React unmount and remount every widget (e.g. a WebGL canvas) whenever the lesson re-renders.
const REMARK_PLUGINS = [remarkGfm];

const Pre = ({ children, node: _node, ...props }: any) => {
  const child: any = Array.isArray(children) ? children[0] : children;
  const cls: string = child?.props?.className ?? "";
  if (cls.startsWith("language-academy:")) return <>{children}</>;
  return <pre {...props}>{children}</pre>;
};

const Code = ({ className, children }: any) => {
  const m = /^language-academy:([\w-]+)/.exec(className ?? "");
  if (m) return <AcademyWidget name={m[1]} body={String(children)} />;
  return <code className={className}>{children}</code>;
};

const AcademyWidget = memo(function AcademyWidget({ name, body }: { name: string; body: string }) {
  const Widget = WIDGETS[name];
  const config = useMemo(() => {
    try { return (yaml.load(body) as any) ?? {}; } catch { return {}; }
  }, [body]);
  return Widget ? <Widget config={config} /> : <div className="text-bad">Unknown widget {name}</div>;
});

const COMPONENTS = { pre: Pre, code: Code };

/** Lesson markdown. Fenced blocks tagged ```academy:<widget> carry YAML config for interactive widgets. */
export const LessonMarkdown = memo(function LessonMarkdown({ source }: { source: string }) {
  return (
    <div className="prose-lesson">
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS} components={COMPONENTS}>
        {source}
      </ReactMarkdown>
    </div>
  );
});
