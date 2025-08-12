"use client";
import React from "react";

const CustomLink = ({ href, children, ...props }: any) => (
  <a
    href={href}
    target="_blank"
    rel="noopener noreferrer"
    className="text-blue-400 hover:text-blue-300 underline underline-offset-2 decoration-blue-400/50 hover:decoration-blue-300 transition-all duration-200 hover:bg-blue-400/10 px-1 py-0.5 rounded"
    {...props}
  >
    {children}
  </a>
);

export default CustomLink;
