using System.IO;
using System.Text;
using UnityEngine;

namespace COA.Game
{
    /// <summary>Parsed world.bytes, written by blender/scripts/export_nature.py. Format documented there.</summary>
    public sealed class WorldData
    {
        public const byte LayerCover = 0, LayerTree = 1, LayerRock = 2, LayerLog = 3;

        public struct Instance { public ushort mesh; public byte layer; public int entity; public Matrix4x4 matrix; }
        public struct Tree { public Vector3 position; public float height, radius; public string kind; }

        public int meshCount;
        public Instance[] instances;
        public Tree[] trees;

        public static WorldData Parse(byte[] bytes)
        {
            using var r = new BinaryReader(new MemoryStream(bytes));
            var magic = Encoding.ASCII.GetString(r.ReadBytes(4));
            if (magic != "COAW") throw new InvalidDataException("world.bytes: bad magic '" + magic + "'");
            uint version = r.ReadUInt32();
            if (version != 1) throw new InvalidDataException("world.bytes: unsupported version " + version);

            var d = new WorldData { meshCount = (int)r.ReadUInt32() };
            d.instances = new Instance[r.ReadUInt32()];
            d.trees = new Tree[r.ReadUInt32()];

            for (int i = 0; i < d.instances.Length; i++)
            {
                var inst = new Instance { mesh = r.ReadUInt16(), layer = r.ReadByte(), entity = r.ReadInt32() };
                var m = new Matrix4x4();
                for (int row = 0; row < 4; row++)
                    for (int col = 0; col < 4; col++)
                        m[row, col] = r.ReadSingle();          // file is row-major
                inst.matrix = m;
                d.instances[i] = inst;
            }
            for (int i = 0; i < d.trees.Length; i++)
            {
                var t = new Tree { position = new Vector3(r.ReadSingle(), r.ReadSingle(), r.ReadSingle()),
                                   height = r.ReadSingle(), radius = r.ReadSingle() };
                t.kind = Encoding.UTF8.GetString(r.ReadBytes(r.ReadByte()));
                d.trees[i] = t;
            }
            return d;
        }
    }
}
