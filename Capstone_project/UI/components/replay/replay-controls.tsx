"use client";

import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import { Button } from "@/components/ui/button";

type ReplayControlsProps = {
  playing: boolean;
  speed: number;
  onPlayingChange: (playing: boolean) => void;
  onStepBack: () => void;
  onStepForward: () => void;
  onSpeedChange: (speed: number) => void;
};

export function ReplayControls({
  playing,
  speed,
  onPlayingChange,
  onStepBack,
  onStepForward,
  onSpeedChange,
}: ReplayControlsProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card p-3">
      <Button size="icon" aria-label={playing ? "Pause replay" : "Resume replay"} onClick={() => onPlayingChange(!playing)}>
        {playing ? <Pause className="h-4 w-4" aria-hidden="true" /> : <Play className="h-4 w-4" aria-hidden="true" />}
      </Button>
      <Button variant="secondary" size="icon" aria-label="Step backward" onClick={onStepBack}>
        <SkipBack className="h-4 w-4" aria-hidden="true" />
      </Button>
      <Button variant="secondary" size="icon" aria-label="Step forward" onClick={onStepForward}>
        <SkipForward className="h-4 w-4" aria-hidden="true" />
      </Button>
      <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
        <span>Speed</span>
        {[1, 2, 4].map((option) => (
          <Button
            key={option}
            variant={speed === option ? "default" : "secondary"}
            size="sm"
            onClick={() => onSpeedChange(option)}
          >
            {option}x
          </Button>
        ))}
      </div>
    </div>
  );
}
