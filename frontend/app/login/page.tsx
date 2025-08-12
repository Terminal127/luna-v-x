"use client";

import React from "react";
import { BackgroundBeams } from "../../components/ui/background-beams";
import { Label } from "../../components/ui/label";
import { Input } from "../../components/ui/input";
import { cn } from "@/lib/utils";
import {
  IconBrandGithub,
  IconBrandGoogle,
  IconBrandOnlyfans,
} from "@tabler/icons-react";

/* ---------------- SIGNUP FORM DEMO ---------------- */
export function SignupFormDemo() {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    console.log("Form submitted");
  };

  return (
    <div className="shadow-lg mx-auto w-full max-w-sm rounded-xl bg-[#1f2335]/95 backdrop-blur-md p-5 md:p-6 border border-[#3b4261]">
      <h2 className="text-xl font-bold text-[#c0caf5]">Welcome to Luna-V-X</h2>
      <p className="mt-1 text-xs text-[#a9b1d6]">
        Login to luna to experience the next gen agentic browsing powered with
        various tools to cater to your needs, Happy browsing!
      </p>

      <form className="my-6 space-y-3" onSubmit={handleSubmit}>
        {/* Name row */}
        <div className="flex gap-2">
          <LabelInputContainer className="flex-1">
            <Label className="text-[#7aa2f7]" htmlFor="firstname">
              First name
            </Label>
            <Input
              className="bg-[#24283b] border border-[#3b4261] text-[#c0caf5] placeholder-[#565f89]"
              id="firstname"
              placeholder="Tyler"
              type="text"
            />
          </LabelInputContainer>
          <LabelInputContainer className="flex-1">
            <Label className="text-[#7aa2f7]" htmlFor="lastname">
              Last name
            </Label>
            <Input
              className="bg-[#24283b] border border-[#3b4261] text-[#c0caf5] placeholder-[#565f89]"
              id="lastname"
              placeholder="Durden"
              type="text"
            />
          </LabelInputContainer>
        </div>

        <LabelInputContainer>
          <Label className="text-[#7aa2f7]" htmlFor="email">
            Email Address
          </Label>
          <Input
            className="bg-[#24283b] border border-[#3b4261] text-[#c0caf5] placeholder-[#565f89]"
            id="email"
            placeholder="projectmayhem@fc.com"
            type="email"
          />
        </LabelInputContainer>

        <LabelInputContainer>
          <Label className="text-[#7aa2f7]" htmlFor="password">
            Password
          </Label>
          <Input
            className="bg-[#24283b] border border-[#3b4261] text-[#c0caf5] placeholder-[#565f89]"
            id="password"
            placeholder="••••••••"
            type="password"
          />
        </LabelInputContainer>

        <LabelInputContainer>
          <Label className="text-[#7aa2f7]" htmlFor="twitterpassword">
            Your twitter password
          </Label>
          <Input
            className="bg-[#24283b] border border-[#3b4261] text-[#c0caf5] placeholder-[#565f89]"
            id="twitterpassword"
            placeholder="••••••••"
            type="password"
          />
        </LabelInputContainer>

        <button
          className="group/btn relative block h-9 w-full rounded-md bg-gradient-to-br from-[#7aa2f7] to-[#bb9af7] font-medium text-sm text-white shadow-md hover:from-[#2ac3de] hover:to-[#9ece6a] transition"
          type="submit"
        >
          Sign up &rarr;
          <BottomGradient />
        </button>

        <div className="my-4 h-[1px] w-full bg-gradient-to-r from-transparent via-[#3b4261] to-transparent" />

        {/* Social row */}
        <div className="flex gap-2">
          <SocialButton icon={<IconBrandGithub />} label="GitHub" />
          <SocialButton icon={<IconBrandGoogle />} label="Google" />
          <SocialButton icon={<IconBrandOnlyfans />} label="OnlyFans" />
        </div>
      </form>
    </div>
  );
}

const SocialButton = ({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: string;
}) => (
  <button
    className="group/btn flex-1 shadow-input relative flex h-9 items-center justify-center space-x-2 rounded-md bg-[#24283b] border border-[#3b4261] px-3 font-medium text-xs text-[#c0caf5] hover:border-[#7aa2f7] transition"
    type="button"
  >
    {React.cloneElement(icon as any, {
      className: "h-3.5 w-3.5 text-[#7aa2f7]",
    })}
    <span>{label}</span>
    <BottomGradient />
  </button>
);

const BottomGradient = () => (
  <>
    <span className="absolute inset-x-0 -bottom-px block h-px w-full bg-gradient-to-r from-transparent via-[#2ac3de] to-transparent opacity-0 transition duration-500 group-hover/btn:opacity-100" />
    <span className="absolute inset-x-10 -bottom-px mx-auto block h-px w-1/2 bg-gradient-to-r from-transparent via-[#bb9af7] to-transparent opacity-0 blur-sm transition duration-500 group-hover/btn:opacity-100" />
  </>
);

const LabelInputContainer = ({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) => (
  <div className={cn("flex w-full flex-col space-y-1.5", className)}>
    {children}
  </div>
);

/* ---------------- PAGE ---------------- */
export default function Page() {
  return (
    <div className="relative min-h-screen w-full bg-[#1a1b26] flex items-center justify-center p-4">
      <div className="z-20 w-full max-w-sm px-2">
        <SignupFormDemo />
      </div>
      <BackgroundBeams />
    </div>
  );
}
