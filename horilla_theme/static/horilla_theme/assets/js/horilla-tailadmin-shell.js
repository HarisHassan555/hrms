/**
 * TailAdmin app shell (Alpine) for Horilla — mirrors TailAdmin index.html body state.
 * Requires Alpine (loaded before this script). Full CSS from tailadmin/build/style.css.
 */
(function () {
  var stored = localStorage.getItem("darkMode");
  if (stored !== null) {
    try {
      var isDark = JSON.parse(stored);
      document.documentElement.classList.toggle("dark", isDark);
      document.body.classList.toggle("dark", isDark);
    } catch (_) {}
  }
})();

document.addEventListener("alpine:init", function () {
  Alpine.data("horillaTailAdminLayout", function () {
    return {
      page: "dsg",
      loaded: true,
      sidebarToggle: false,
      darkMode: document.documentElement.classList.contains("dark"),
      init: function () {
        var self = this;
        this.$watch("darkMode", function (value) {
          document.documentElement.classList.toggle("dark", value);
          document.body.classList.toggle("dark", value);
          try {
            localStorage.setItem("darkMode", JSON.stringify(value));
          } catch (_) {}
        });
        document.addEventListener("horilla:theme-changed", function (e) {
          if (e.detail && typeof e.detail.dark === "boolean") {
            self.darkMode = e.detail.dark;
          }
        });
      },
    };
  });
});
