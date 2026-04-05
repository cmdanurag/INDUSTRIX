import React from 'react';

interface NormalDistributionChartProps {
  mean: number;
  sigma: number;
  height?: number;
  width?: number;
}

export const NormalDistributionChart: React.FC<NormalDistributionChartProps> = ({ 
  mean, 
  sigma, 
  height = 60, 
  width = 240 
}) => {
  // Gaussian function
  const gaussian = (x: number, m: number, s: number) => {
    const s_safe = Math.max(0.5, s);
    const exponent = -0.5 * Math.pow((x - m) / s_safe, 2);
    return (1 / (s_safe * Math.sqrt(2 * Math.PI))) * Math.exp(exponent);
  };

  // Generate points for the curve
  const points: [number, number][] = [];
  const resolution = 50; 
  
  const yMax = gaussian(mean, mean, sigma);
  const padding = 5;
  const drawHeight = height - padding * 2;

  for (let i = 0; i <= resolution; i++) {
    const x = (i / resolution) * 100;
    const yVal = gaussian(x, mean, sigma);
    
    // Safety check for calculation failures
    const normalizedY = isFinite(yVal / yMax) ? (yVal / yMax) : 0;
    const y = height - padding - normalizedY * drawHeight;
    const xCanvas = (x / 100) * width;
    points.push([xCanvas, y]);
  }

  const pathData = points.length > 0 
    ? `M ${points[0][0]},${points[0][1]} ` + points.slice(1).map(p => `L ${p[0]},${p[1]}`).join(' ')
    : 'M 0,0';

  const meanX = isFinite(mean) ? (mean / 100) * width : 0;

  return (
    <div className="relative group cursor-crosshair">
      <svg width={width} height={height} className="overflow-visible">
        {/* Background Grid */}
        {[0, 25, 50, 75, 100].map((tick) => (
          <line
            key={tick}
            x1={(tick / 100) * width}
            y1={0}
            x2={(tick / 100) * width}
            y2={height}
            stroke="currentColor"
            className="text-on-surface/5"
            strokeWidth="1"
          />
        ))}

        {/* Shaded Area */}
        <path
          d={`${pathData} L ${width},${height} L 0,${height} Z`}
          fill="url(#grad-distribution)"
          className="opacity-20"
        />

        {/* The Curve */}
        <path
          d={pathData}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="text-primary"
        />

        {/* Mean Indicator */}
        <line
          x1={meanX}
          y1={0}
          x2={meanX}
          y2={height}
          stroke="currentColor"
          strokeDasharray="2 2"
          className="text-primary/60"
        />

        <defs>
          <linearGradient id="grad-distribution" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.8" />
            <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
      
      {/* Label Overlays */}
      <div className="absolute top-1 left-1 text-[8px] font-mono text-on-surface-variant uppercase opacity-50">
        Grade Prob. Distribution
      </div>
      <div className="absolute bottom-1 right-1 text-[9px] font-mono text-primary font-bold">
        μ={mean.toFixed(1)} σ={sigma.toFixed(1)}
      </div>
    </div>
  );
};
