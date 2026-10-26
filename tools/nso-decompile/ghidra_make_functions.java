// ghidra_make_functions.java — Ghidra headless pre-script for bare NSO ELFs.
//
// Stripped NSO images carry no symbols (dynsym is empty), so auto-analysis
// creates no functions and the decompiler has nothing to work on.  This
// script sweep-disassembles every executable block (on AArch64 every word
// decodes, so the sweep is complete) and creates a function at the image
// entry and at every direct branch/call target.  Runs *before* analysis;
// decompile.sh passes it with -preScript.
//
//@category Analysis
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;

import java.util.Set;
import java.util.TreeSet;

public class ghidra_make_functions extends GhidraScript {

    @Override
    public void run() throws Exception {
        // 1. sweep-disassemble every executable block
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (!block.isExecute())
                continue;
            Address a = block.getStart();
            while (a != null && a.compareTo(block.getEnd()) <= 0
                   && !monitor.isCancelled()) {
                disassemble(a);
                Instruction ins = getInstructionAt(a);
                a = (ins == null) ? a.add(4) : a.add(ins.getLength());
            }
        }

        // 2. collect the entry plus every flow (branch/call) target that
        //    lands inside an executable block
        Set<Long> starts = new TreeSet<Long>();
        Address entry = currentProgram.getImageBase();
        if (entry != null)
            starts.add(entry.getOffset());
        for (Instruction ins :
             currentProgram.getListing().getInstructions(true)) {
            if (monitor.isCancelled())
                break;
            for (Reference ref : ins.getReferencesFrom()) {
                if (!ref.getReferenceType().isFlow())
                    continue;
                MemoryBlock to =
                    currentProgram.getMemory().getBlock(ref.getToAddress());
                if (to != null && to.isExecute())
                    starts.add(ref.getToAddress().getOffset());
            }
        }

        // 3. create functions (skip targets already covered by one)
        for (long off : starts) {
            Address a = currentProgram.getAddressFactory()
                          .getDefaultAddressSpace().getAddress(off);
            if (monitor.isCancelled())
                break;
            if (getFunctionAt(a) != null || getFunctionContaining(a) != null)
                continue;
            try {
                createFunction(a, null);
            } catch (Exception e) {
                // odd/overlapping target — analysis will cope
            }
        }
        println("ghidra make-functions: " + starts.size() + " entry points, "
                + currentProgram.getFunctionManager().getFunctionCount()
                + " functions created");
    }
}
