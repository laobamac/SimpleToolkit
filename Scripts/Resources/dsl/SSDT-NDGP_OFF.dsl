//
DefinitionBlock("", "SSDT", 2, "OCLT", "DPCI", 0)
{
    External(_{ADDR}._ON, MethodObj)
    External(_{ADDR}._OFF, MethodObj)
 
    If (_OSI ("Darwin"))
    {
        Device(DGPU)
        {
            Name(_HID, "DGPU1000")
            Method (_INI, 0, NotSerialized)
            {
                _OFF()
            }
            
            Method (_ON, 0, NotSerialized)
            {
                //path:
                If (CondRefOf (\_{ADDR}._ON))
                {
                    \_{ADDR}._ON()
                }
            }
            
            Method (_OFF, 0, NotSerialized)
            {
                //path:
                If (CondRefOf (\_{ADDR}._OFF))
                {
                    \_{ADDR}._OFF()
                }
            }
        }
    }
}
//EOF
