'use client';

// ============================================================
// Shia — Main Application Page
// Wires the pipeline orchestrator into the UI components
// ============================================================

import { usePipeline } from '@/hooks/usePipeline';
import Header from '@/components/SignAI/Header';
import VisionMatrix from '@/components/SignAI/VisionMatrix';
import QuickActions from '@/components/SignAI/QuickActions';
import TranscriptLog from '@/components/SignAI/TranscriptLog';
import Footer from '@/components/SignAI/Footer';

export default function Home() {
  const {
    // Pipeline state
    isActive,
    mode,
    logs,

    // Pipeline actions
    startPipeline,
    stopPipeline,
    toggleMode,
    sendManualInput,
    processGestureResult,
  } = usePipeline();

  const handleToggleSystem = () => {
    if (isActive) {
      stopPipeline();
    } else {
      startPipeline();
    }
  };

  return (
    <div className="bg-pixel-grid min-h-screen p-4 md:p-8 font-mono">
      {/* Header — System Controls */}
      <Header
        isSystemActive={isActive}
        mode={mode}
        onToggleMode={toggleMode}
        onToggleSystem={handleToggleSystem}
      />

      {/* Main Terminal UI */}
      <main className="grid grid-cols-1 lg:grid-cols-12 gap-8 max-w-7xl mx-auto">
        {/* Left Column: Vision + Quick Actions */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <VisionMatrix
            isActive={isActive}
            onGestureResult={processGestureResult}
          />
          <QuickActions isActive={isActive} />
        </div>

        {/* Right Column: Transcript Log */}
        <div className="lg:col-span-5">
          <TranscriptLog
            logs={logs}
            isActive={isActive}
            onManualInput={sendManualInput}
          />
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}
