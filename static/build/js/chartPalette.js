/**
 * Shared soft chart palette — matches "Needs Your Attention" pastel cards
 * (light fills, not saturated solid bars/donut slices).
 *
 * Use window.HORILLA_CHART_COLORS anywhere ApexCharts / Chart.js needs a series palette.
 */
(function (global) {
  "use strict";

  var LIGHT = [
    "#A5B4FC", // indigo soft
    "#93C5FD", // sky soft
    "#5EEAD4", // teal soft
    "#86EFAC", // green soft
    "#FCD34D", // amber soft
    "#FCA5A5", // red soft
    "#D8B4FE", // purple soft
    "#F9A8D4", // pink soft
    "#67E8F9", // cyan soft
    "#FDBA74", // orange soft
  ];

  var STATUS = {
    active: "#86EFAC",
    inactive: "#FCA5A5",
    success: "#86EFAC",
    warning: "#FCD34D",
    danger: "#FCA5A5",
    info: "#93C5FD",
    neutral: "#CBD5E1",
  };

  var STAGE = {
    initial: "#CBD5E1",
    applied: "#A5B4FC",
    test: "#93C5FD",
    interview: "#FCD34D",
    hired: "#86EFAC",
    cancelled: "#FCA5A5",
  };

  global.HORILLA_CHART_COLORS = LIGHT;
  global.HORILLA_CHART_STATUS = STATUS;
  global.HORILLA_CHART_STAGE = STAGE;
})(typeof window !== "undefined" ? window : this);
