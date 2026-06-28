using System;

namespace HonestDamage.Plugin
{
    /// <summary>
    /// Locates the local player's XAttribsCMP and XEntity at runtime.
    ///
    /// Strategy: XAttribsCMP / XEntity are not MonoBehaviours so FindObjectsOfType cannot
    /// be used.  The TakeDamage postfix hook (Diagnostics.cs) populates _cached whenever
    /// it observes a player entity taking damage.  Player discrimination uses XPlayerCMP:
    /// only player entities carry this component; enemies do not.  This is confirmed in
    /// both the dump.cs decompile and the interop Assembly-CSharp.dll proxy.
    ///
    /// On first F9 press before the player has taken any damage, _cached will be null;
    /// the log warns and the user can press F9 again after taking a hit.
    ///
    /// Remaining concern: in co-op, multiple players may hit the cache sequentially —
    /// the last player hit wins.  In solo play this is always the local player.
    /// </summary>
    public static class PlayerLocator
    {
        private static GameCode.XAttribsCMP? _cached;
        private static GameCode.XEntity?     _cachedEntity;

        /// <summary>Called by the TakeDamage hook to seed the cache.</summary>
        internal static void Seed(GameCode.XEntity entity, GameCode.XAttribsCMP cmp)
        {
            _cachedEntity = entity;
            _cached       = cmp;
        }

        // Backward-compat overload (attribs-only seed; entity stays unchanged).
        internal static void Seed(GameCode.XAttribsCMP cmp)
        {
            _cached = cmp;
        }

        /// <summary>
        /// Returns the local player's XAttribsCMP, or null if not yet located.
        /// </summary>
        public static GameCode.XAttribsCMP? GetLocalAttribs()
        {
            if (_cached != null)
                return _cached;

            Plugin.Log.LogWarning("[PlayerLocator] XAttribsCMP not yet cached. " +
                "Take a hit in-game first, then press F9 to dump diagnostics.");
            return null;
        }

        /// <summary>
        /// Returns the local player's XEntity, or null if not yet located.
        /// Needed by InventoryInjector / Diagnostics for weapon-attack queries.
        /// </summary>
        public static GameCode.XEntity? GetLocalEntity()
        {
            return _cachedEntity;
        }
    }
}
