import React from "react";
import CodeBlock from "./CodeBlock";
import CustomLink from "./CustomLink";

export const markdownComponents = {
  code: ({ inline, className, children, ...props }: any) => {
    return !inline ? (
      <CodeBlock className={className} {...props}>
        {children}
      </CodeBlock>
    ) : (
      <code
        className={`px-1 py-0.5 rounded bg-neutral-800 text-gray-100 ${className || ""}`}
        {...props}
      >
        {children}
      </code>
    );
  },
  a: (props: any) => <CustomLink {...props} />,
  p: (props: any) => (
    <p
      className="mb-4 text-sm leading-relaxed text-gray-100 whitespace-pre-wrap"
      {...props}
    />
  ),
  ul: (props: any) => (
    <ul
      className="list-disc list-outside ml-6 mb-4 text-sm space-y-1.5 text-gray-100"
      {...props}
    />
  ),
  ol: (props: any) => (
    <ol
      className="list-decimal list-outside ml-6 mb-4 text-sm space-y-1.5 text-gray-100"
      {...props}
    />
  ),
  li: (props: any) => (
    <li className="text-sm leading-relaxed text-gray-100 pl-1" {...props} />
  ),
  h1: (props: any) => (
    <h1
      className="text-xl font-bold mb-4 mt-6 text-blue-300 border-b border-blue-300/30 pb-2"
      {...props}
    />
  ),
  h2: (props: any) => (
    <h2 className="text-lg font-semibold mb-3 mt-5 text-blue-300" {...props} />
  ),
  blockquote: (props: any) => (
    <blockquote
      className="border-l-4 border-blue-400/50 pl-4 py-2 mb-4 text-sm italic bg-blue-400/5 rounded-r text-gray-200"
      {...props}
    />
  ),
  table: (props: any) => (
    <div className="overflow-x-auto mb-4">
      <table
        className="min-w-full border border-neutral-600 rounded-lg overflow-hidden"
        {...props}
      />
    </div>
  ),
  thead: (props: any) => <thead className="bg-neutral-700" {...props} />,
  tbody: (props: any) => <tbody className="bg-neutral-800/50" {...props} />,
  tr: (props: any) => (
    <tr
      className="border-b border-neutral-600 hover:bg-neutral-700/30"
      {...props}
    />
  ),
  th: (props: any) => (
    <th
      className="px-4 py-2 text-left text-sm font-semibold text-gray-200 border-r border-neutral-600 last:border-r-0"
      {...props}
    />
  ),
  td: (props: any) => (
    <td
      className="px-4 py-2 text-sm text-gray-200 border-r border-neutral-600 last:border-r-0"
      {...props}
    />
  ),
  hr: () => <hr className="my-6 border-neutral-600" />,
};
