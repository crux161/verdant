// ghidra_probe.java — diagnostics: report program state in the saved project.
//
//@category Analysis
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;

public class ghidra_probe extends GhidraScript {

    @Override
    public void run() throws Exception {
        println("FUNCTIONS: "
                + currentProgram.getFunctionManager().getFunctionCount());
        println("INSTRUCTIONS: "
                + currentProgram.getListing().getNumInstructions());
        int n = 0;
        for (Function f :
             currentProgram.getFunctionManager().getFunctions(true)) {
            if (n++ >= 5)
                break;
            println("F " + f.getEntryPoint() + " " + f.getName());
        }

        Function first =
            currentProgram.getFunctionManager().getFunctions(true).next();
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        DecompileResults res = ifc.decompileFunction(first, 90, monitor);
        println("DECOMPILE completed=" + res.decompileCompleted());
        println("DECOMPILE error=" + res.getErrorMessage());
    }
}
