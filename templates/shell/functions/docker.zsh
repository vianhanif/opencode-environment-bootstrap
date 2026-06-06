# =========================================================
# DOCKER / COLIMA FUNCTIONS
# =========================================================

colima() {
  killall -9 system_profiler 2>/dev/null
  command colima "$@"
}
