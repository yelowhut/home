namespace HonestDamage.Core
{
    public readonly struct Modifier
    {
        public readonly Attrib Attrib;
        public readonly float Value;
        public readonly ModOp Op;

        public Modifier(Attrib attrib, float value, ModOp op)
        {
            Attrib = attrib;
            Value = value;
            Op = op;
        }
    }
}
