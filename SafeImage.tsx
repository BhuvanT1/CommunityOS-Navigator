import { useState } from 'react';
import { AlertCircle } from 'lucide-react';

interface SafeImageProps {
  src?: string | null;
  alt: string;
  className?: string;
  fallbackClassName?: string;
}

export function SafeImage({ src, alt, className = "", fallbackClassName = "" }: SafeImageProps) {
  const [error, setError] = useState(false);

  if (!src || error) {
    return (
      <div className={`flex flex-col items-center justify-center text-zinc-500 bg-zinc-900 w-full h-full ${fallbackClassName}`}>
        <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
        <span className="text-xs font-medium tracking-wider uppercase">No Image Available</span>
      </div>
    );
  }

  return (
    <img 
      src={src} 
      alt={alt} 
      className={className} 
      onError={() => setError(true)} 
    />
  );
}
