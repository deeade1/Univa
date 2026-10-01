import React, { useEffect, useState } from "react";
import Lottie from "lottie-react";
import lottieData from "@/assets/animations/loader.json";

interface LoaderProps {
  show: boolean;
  type?: "svg" | "lottie";
}

const Loader: React.FC<LoaderProps> = ({ show, type = "svg" }) => {
  const [visible, setVisible] = useState(show);

  useEffect(() => {
    if (show) {
      setVisible(true);
    } else {
      // Delay unmount until after fade-out
      const timeout = setTimeout(() => setVisible(false), 400); // match SCSS transition
      return () => clearTimeout(timeout);
    }
  }, [show]);

  if (!visible) return null;

  return (
    <div className={`loader simple-loader ${!show ? "fade-out" : ""}`}>
      <div className="loader-body">
        {type === "svg" ? (
          <svg
            width="80"
            height="80"
            viewBox="0 0 44 44"
            xmlns="http://www.w3.org/2000/svg"
            stroke="#3b82f6"
          >
            <g fill="none" fillRule="evenodd" strokeWidth="2">
              <circle cx="22" cy="22" r="1">
                <animate
                  attributeName="r"
                  begin="0s"
                  dur="1.8s"
                  values="1; 20"
                  calcMode="spline"
                  keyTimes="0; 1"
                  keySplines="0.165, 0.84, 0.44, 1"
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="stroke-opacity"
                  begin="0s"
                  dur="1.8s"
                  values="1; 0"
                  calcMode="spline"
                  keyTimes="0; 1"
                  keySplines="0.3, 0.61, 0.355, 1"
                  repeatCount="indefinite"
                />
              </circle>
              <circle cx="22" cy="22" r="1">
                <animate
                  attributeName="r"
                  begin="-0.9s"
                  dur="1.8s"
                  values="1; 20"
                  calcMode="spline"
                  keyTimes="0; 1"
                  keySplines="0.165, 0.84, 0.44, 1"
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="stroke-opacity"
                  begin="-0.9s"
                  dur="1.8s"
                  values="1; 0"
                  calcMode="spline"
                  keyTimes="0; 1"
                  keySplines="0.3, 0.61, 0.355, 1"
                  repeatCount="indefinite"
                />
              </circle>
            </g>
          </svg>
        ) : (
          <Lottie animationData={lottieData} loop style={{ width: 100, height: 100 }} />
        )}
      </div>
    </div>
  );
};

export default Loader;
