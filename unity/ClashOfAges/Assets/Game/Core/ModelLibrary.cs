using System.Collections.Generic;
using UnityEngine;

namespace COA.Game
{
    /// <summary>name -> prefab, filled by DemoSceneBuilder. Runtime cannot load from Assets/Models by path.</summary>
    public sealed class ModelLibrary : MonoBehaviour
    {
        public List<string> names = new List<string>();
        public List<GameObject> prefabs = new List<GameObject>();
        public Material ghostOk, ghostBad, ring, ringEnemy, marker, blood, stump, border, particle, arrow, hpBack, hpFill;

        Dictionary<string, GameObject> _map;
        public GameObject Get(string name)
        {
            if (_map == null) { _map = new Dictionary<string, GameObject>(); for (int i = 0; i < names.Count; i++) _map[names[i]] = prefabs[i]; }
            return _map.TryGetValue(name, out var go) ? go : null;
        }
    }
}
