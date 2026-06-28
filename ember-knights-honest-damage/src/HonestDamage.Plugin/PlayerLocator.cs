using System;

namespace HonestDamage.Plugin
{
    /// <summary>
    /// Locates the local player's XAttribsCMP at runtime.
    ///
    /// Strategy (runtime-confirm): XAttribsCMP is not a MonoBehaviour so
    /// FindObjectsOfType cannot be used. Instead we rely on a two-phase approach:
    ///
    ///   1. The TakeDamage postfix hook (Diagnostics.cs) populates _cached
    ///      whenever it observes player attribs. On first F9 press before any
    ///      combat, cache will be null — the log will warn and the user can
    ///      press F9 again mid-fight.
    ///
    ///   2. Future refinement via XWorld.GetCMPGroup once the runtime API
    ///      surface is confirmed from the diagnostic dump.
    /// </summary>
    public static class PlayerLocator
    {
        private static GameCode.XAttribsCMP? _cached;

        /// <summary>Called by the TakeDamage hook to seed the cache.</summary>
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
    }
}
