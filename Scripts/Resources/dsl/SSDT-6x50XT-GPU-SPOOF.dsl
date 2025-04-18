/*
 * Intel ACPI Component Architecture
 * AML/ASL+ Disassembler version 20241212 (32-bit version)
 * Copyright (c) 2000 - 2023 Intel Corporation
 * 
 * Disassembling to symbolic ASL+ operators
 *
 * Disassembly of SSDT-SH-SPOOF.aml
 *
 * Original Table Header:
 *     Signature        "SSDT"
 *     Length           0x000000B9 (185)
 *     Revision         0x02
 *     Checksum         0x94
 *     OEM ID           "hack"
 *     OEM Table ID     "spoof1"
 *     OEM Revision     0x00000000 (0)
 *     Compiler ID      "INTL"
 *     Compiler Version 0x20200925 (538970405)
 */
DefinitionBlock ("", "SSDT", 2, "hack", "spoof1", 0x00000000)
{
    External (_{ADDR}.PEGP, DeviceObj)

    Device (_{ADDR}.PEGP.PBR0)
    {
        Name (_ADR, Zero)  // _ADR: Address
        Device (GFX1)
        {
            Name (_ADR, Zero)  // _ADR: Address
        }
    }

    Method (_{ADDR}.PEGP.PBR0.GFX1._DSM, 4, NotSerialized)  // _DSM: Device-Specific Method
    {
        If ((!Arg2 || !_OSI ("Darwin")))
        {
            Return (Buffer (One)
            {
                 0x03                                             // .
            })
        }

        Return (Package (0x02)
        {
            "device-id", 
            Buffer (0x04)
            {
                 0xAB, 0xCD, 0x00, 0x00                           // .s..
            }
        })
    }
}

