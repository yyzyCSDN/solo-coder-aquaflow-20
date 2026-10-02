import unittest
from aquaflow.api import AquaFlowService
from aquaflow.network.isolation import Pipe,isolated
from aquaflow.workflow_rules import evaluate
class ReversedEndpoints(unittest.TestCase):
    def test_reversed_pipes_still_supply(self):
        # topology records both pipes downstream-first; open pipes are undirected
        ps=[Pipe("1","A","S"),Pipe("2","B","A")]
        self.assertEqual(isolated({"S","A","B"},ps,set(),{"S"}),set())
    def test_mixed_orientation_path(self):
        ps=[Pipe("1","S","A"),Pipe("2","B","A"),Pipe("3","B","C")]
        self.assertEqual(isolated({"S","A","B","C"},ps,set(),{"S"}),set())
    def test_reversed_pipe_reachable_from_either_side(self):
        ps=[Pipe("1","B","A")]
        self.assertEqual(isolated({"S","A","B"},[Pipe("0","S","B")]+ps,set(),{"S"}),set())
class ClosedCuts(unittest.TestCase):
    def test_closed_valve_cuts(self):
        ps=[Pipe("1","S","A"),Pipe("2","A","B")]
        self.assertEqual(isolated({"S","A","B"},ps,{"2"},{"S"}),{"B"})
    def test_closed_valve_cuts_reversed_pipe(self):
        ps=[Pipe("1","A","S"),Pipe("2","B","A")]
        self.assertEqual(isolated({"S","A","B"},ps,{"1"},{"S"}),{"A","B"})
    def test_unopened_pipe_cuts(self):
        ps=[Pipe("1","S","A"),Pipe("2","A","B",open=False)]
        self.assertEqual(isolated({"S","A","B"},ps,set(),{"S"}),{"B"})
    def test_reopened_valve_restores(self):
        ps=[Pipe("1","S","A"),Pipe("2","A","B")]
        self.assertEqual(isolated({"S","A","B"},ps,set(),{"S"}),set())
class DualSource(unittest.TestCase):
    def ring(self):return [Pipe("1","S1","A"),Pipe("2","A","B"),Pipe("3","B","S2")]
    def test_both_sources_supply_ring(self):
        self.assertEqual(isolated({"S1","S2","A","B"},self.ring(),set(),{"S1","S2"}),set())
    def test_one_source_remaining(self):
        # S1 link cut: A and B must still be supplied from S2
        self.assertEqual(isolated({"S1","S2","A","B"},self.ring(),{"1"},{"S1","S2"}),set())
    def test_one_source_remaining_reversed_endpoints(self):
        ps=[Pipe("1","A","S1"),Pipe("2","B","A"),Pipe("3","S2","B")]
        self.assertEqual(isolated({"S1","S2","A","B"},ps,{"1"},{"S1","S2"}),set())
    def test_both_sources_cut(self):
        self.assertEqual(isolated({"S1","S2","A","B"},self.ring(),{"1","3"},{"S1","S2"}),{"A","B"})
    def test_single_source_after_source_loss(self):
        # only S2 remains available; nodes behind the cut near S1 go dry
        ps=[Pipe("1","S1","A"),Pipe("2","A","B"),Pipe("3","B","S2")]
        self.assertEqual(isolated({"S1","S2","A","B"},ps,{"1","2"},{"S2"}),{"S1","A"})
class IsolationReport(unittest.TestCase):
    def payload(self):
        return {"nodes":["S","A","B","C"],
                "pipes":[{"id":"1","a":"A","b":"S"},{"id":"2","a":"B","b":"A"},{"id":"3","a":"C","b":"B"}],
                "closed":["2","3"],"sources":["S"]}
    def test_service_returns_set(self):
        self.assertEqual(AquaFlowService().isolate({"S","A","B"},[Pipe("1","S","A"),Pipe("2","A","B")],{"2"},{"S"}),{"B"})
    def test_workflow_report_sorted_and_deterministic(self):
        svc=AquaFlowService()
        first=svc.run_workflow("network_isolation",self.payload())
        second=svc.run_workflow("network_isolation",self.payload())
        self.assertEqual(first["value"],["B","C"])
        self.assertEqual(first["value"],second["value"])
    def test_workflow_reversed_endpoints_nothing_isolated(self):
        r=AquaFlowService().run_workflow("network_isolation",
            {"nodes":["S","A","B"],"pipes":[{"id":"1","a":"A","b":"S"},{"id":"2","a":"B","b":"A"}],"closed":[],"sources":["S"]})
        self.assertEqual(r["value"],[])
    def test_evaluate_without_prestamped_payload(self):
        # evaluate must honor each pipe's own open flag, no envelope magic required
        r=evaluate("network_isolation",{"nodes":["S","A"],"pipes":[{"id":"1","a":"S","b":"A"}],"closed":[],"sources":["S"]})
        self.assertEqual(r["value"],[])
if __name__=="__main__":unittest.main()
