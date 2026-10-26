// ghidra_export_all.java — Ghidra headless post-script.
//
// Decompiles every function to C (one file per function) and writes a
// symbol table.  Run through decompile.sh:
//
//   analyzeHeadless <projdir> ghidra -import binary.elf \
//       -scriptPath <tools/nso-decompile> \
//       -postScript ghidra_export_all.java <outdir>
//
//@category Analysis
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolTable;

import java.io.File;
import java.io.PrintWriter;

public class ghidra_export_all extends GhidraScript {

    @Override
    public void run() throws Exception {
        String out = getScriptArgs()[0];
        File cDir = new File(out, "c");
        cDir.mkdirs();

        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);

        int done = 0, failed = 0;
        FunctionIterator it =
            currentProgram.getFunctionManager().getFunctions(true);
        while (it.hasNext() && !monitor.isCancelled()) {
            Function f = it.next();
            monitor.setMessage("decompiling " + f.getName());
            DecompileResults res = ifc.decompileFunction(f, 90, monitor);
            if (res != null && res.decompileCompleted()) {
                String name = f.getName().replaceAll("[^A-Za-z0-9_.-]", "_");
                File file = new File(cDir, String.format(
                    "%08x_%s.c", f.getEntryPoint().getOffset(), name));
                try (PrintWriter pw = new PrintWriter(file)) {
                    pw.print(res.getDecompiledFunction().getC());
                }
                done++;
            } else {
                failed++;
            }
        }

        try (PrintWriter pw = new PrintWriter(
                 new File(out, "symbols.csv"))) {
            pw.println("address,name,type");
            SymbolTable st = currentProgram.getSymbolTable();
            for (Symbol sym : st.getAllSymbols(false)) {
                pw.printf("%08x,%s,%s%n", sym.getAddress().getOffset(),
                          sym.getName(), sym.getSymbolType());
            }
        }

        println("ghidra export: " + done + " functions decompiled, " +
                failed + " failed");
    }
}
