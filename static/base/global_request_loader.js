/**
 * App-wide loading overlay for HTMX, fetch, and jQuery AJAX.
 *
 * Opt out:
 *   - data-no-global-loader on a trigger element or ancestor
 *   - fetch(..., { hrmsNoGlobalLoader: true })
 *   - Header X-HRMS-No-Global-Loader: 1
 *   - jQuery ajax: { hrmsNoGlobalLoader: true }
 *
 * GET fetch/ajax only show the loader when hrmsGlobalLoader: true (mutating
 * methods always show unless opted out).
 */
(function (global) {
  "use strict";

  var activeCount = 0;
  var root = null;

  function getRoot() {
    if (!root) {
      root = document.getElementById("hrms-global-loader");
    }
    return root;
  }

  function syncDom() {
    var el = getRoot();
    if (!el) {
      return;
    }
    var busy = activeCount > 0;
    el.hidden = !busy;
    el.setAttribute("aria-busy", busy ? "true" : "false");
  }

  function show() {
    activeCount += 1;
    syncDom();
  }

  function hide() {
    activeCount = Math.max(0, activeCount - 1);
    syncDom();
  }

  function optedOutFromHeaders(headers) {
    if (!headers) {
      return false;
    }
    try {
      if (headers instanceof Headers) {
        return headers.get("X-HRMS-No-Global-Loader") === "1";
      }
      if (Array.isArray(headers)) {
        for (var i = 0; i < headers.length; i += 1) {
          var pair = headers[i];
          if (
            pair &&
            String(pair[0]).toLowerCase() === "x-hrms-no-global-loader" &&
            String(pair[1]) === "1"
          ) {
            return true;
          }
        }
        return false;
      }
      var val = headers["X-HRMS-No-Global-Loader"] || headers["x-hrms-no-global-loader"];
      return val === "1" || val === 1;
    } catch (e) {
      return false;
    }
  }

  function elementOptedOut(elt) {
    if (!elt || !elt.closest) {
      return false;
    }
    return !!elt.closest("[data-no-global-loader]");
  }

  function shouldTrackFetch(input, init) {
    init = init || {};
    if (init.hrmsNoGlobalLoader) {
      return false;
    }
    if (optedOutFromHeaders(init.headers)) {
      return false;
    }
    var method = (init.method || "GET").toUpperCase();
    if (method === "GET" || method === "HEAD") {
      return !!init.hrmsGlobalLoader;
    }
    return true;
  }

  function shouldTrackJqueryAjax(settings) {
    if (!settings || settings.hrmsNoGlobalLoader) {
      return false;
    }
    if (optedOutFromHeaders(settings.headers)) {
      return false;
    }
    var method = (settings.type || settings.method || "GET").toUpperCase();
    if (method === "GET" || method === "HEAD") {
      return !!settings.hrmsGlobalLoader;
    }
    return true;
  }

  function bindHtmx() {
    document.body.addEventListener("htmx:beforeRequest", function (evt) {
      var detail = evt.detail || {};
      var elt = detail.elt;
      if (elementOptedOut(elt) || optedOutFromHeaders(detail.headers)) {
        detail._hrmsSkipLoader = true;
        return;
      }
      detail._hrmsTrackedLoader = true;
      show();
    });

    document.body.addEventListener("htmx:afterRequest", function (evt) {
      var detail = evt.detail || {};
      if (detail._hrmsTrackedLoader) {
        detail._hrmsTrackedLoader = false;
        hide();
      }
    });

    document.body.addEventListener("htmx:sendError", function (evt) {
      var detail = evt.detail || {};
      if (detail._hrmsTrackedLoader) {
        detail._hrmsTrackedLoader = false;
        hide();
      }
    });
  }

  function patchFetch() {
    if (!global.fetch || global.fetch.__hrmsLoaderPatched) {
      return;
    }
    var nativeFetch = global.fetch.bind(global);
    global.fetch = function (input, init) {
      var track = shouldTrackFetch(input, init);
      if (track) {
        show();
      }
      return nativeFetch(input, init).then(
        function (res) {
          if (track) {
            hide();
          }
          return res;
        },
        function (err) {
          if (track) {
            hide();
          }
          throw err;
        }
      );
    };
    global.fetch.__hrmsLoaderPatched = true;
  }

  function bindJquery() {
    if (!global.jQuery) {
      return;
    }
    global.jQuery(document).on("ajaxSend", function (_evt, _jqXHR, settings) {
      if (shouldTrackJqueryAjax(settings)) {
        show();
      }
    });
    global.jQuery(document).on("ajaxComplete ajaxError", function (_evt, _jqXHR, settings) {
      if (shouldTrackJqueryAjax(settings)) {
        hide();
      }
    });
  }

  global.HRMSRequestLoader = {
    show: show,
    hide: hide,
  };

  function init() {
    bindHtmx();
    patchFetch();
    bindJquery();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
