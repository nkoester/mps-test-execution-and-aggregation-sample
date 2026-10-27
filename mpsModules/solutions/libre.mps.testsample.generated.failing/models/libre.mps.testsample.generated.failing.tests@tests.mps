<?xml version="1.0" encoding="UTF-8"?>
<model ref="r:f23f390e-3b3b-4cdd-8777-5317f8270687(libre.mps.testsample.generated.failing.tests@tests)">
  <persistence version="9" />
  <languages>
    <use id="8585453e-6bfb-4d80-98de-b16074f1d86c" name="jetbrains.mps.lang.test" version="6" />
    <use id="f61473f9-130f-42f6-b98d-6c438812c2f6" name="jetbrains.mps.baseLanguage.unitTest" version="1" />
    <use id="9464fa06-5ab9-409b-9274-64ab29588457" name="org.iets3.core.expr.lambda" version="6" />
    <use id="71934284-d7d1-45ee-a054-8c072591085f" name="org.iets3.core.expr.toplevel" version="8" />
    <use id="cfaa4966-b7d5-4b69-b66a-309a6e1a7290" name="org.iets3.core.expr.base" version="22" />
    <use id="d441fba0-f46b-43cd-b723-dad7b65da615" name="org.iets3.core.expr.tests" version="6" />
    <use id="6b277d9a-d52d-416f-a209-1919bd737f50" name="org.iets3.core.expr.simpleTypes" version="11" />
  </languages>
  <imports />
  <registry>
    <language id="cfaa4966-b7d5-4b69-b66a-309a6e1a7290" name="org.iets3.core.expr.base">
      <concept id="5115872837156578671" name="org.iets3.core.expr.base.structure.MulExpression" flags="ng" index="30dDTi" />
      <concept id="5115872837156578546" name="org.iets3.core.expr.base.structure.PlusExpression" flags="ng" index="30dDZf" />
      <concept id="5115872837156576277" name="org.iets3.core.expr.base.structure.BinaryExpression" flags="ng" index="30dEsC">
        <child id="5115872837156576280" name="right" index="30dEs_" />
        <child id="5115872837156576278" name="left" index="30dEsF" />
      </concept>
    </language>
    <language id="d441fba0-f46b-43cd-b723-dad7b65da615" name="org.iets3.core.expr.tests">
      <concept id="543569365052056273" name="org.iets3.core.expr.tests.structure.EqualsTestOp" flags="ng" index="_fku$" />
      <concept id="543569365052056263" name="org.iets3.core.expr.tests.structure.TestCase" flags="ng" index="_fkuM">
        <child id="543569365052056368" name="items" index="_fkp5" />
      </concept>
      <concept id="543569365052056266" name="org.iets3.core.expr.tests.structure.AssertTestItem" flags="ng" index="_fkuZ">
        <child id="543569365052056302" name="op" index="_fkur" />
        <child id="543569365052056269" name="expected" index="_fkuS" />
        <child id="543569365052056267" name="actual" index="_fkuY" />
      </concept>
      <concept id="543569365052711055" name="org.iets3.core.expr.tests.structure.TestSuite" flags="ng" index="_iOnU">
        <property id="8811147530091989932" name="executeAutomatically" index="2SXJ1i" />
        <child id="543569365052711058" name="contents" index="_iOnB" />
      </concept>
    </language>
    <language id="6b277d9a-d52d-416f-a209-1919bd737f50" name="org.iets3.core.expr.simpleTypes">
      <concept id="8219602584782245544" name="org.iets3.core.expr.simpleTypes.structure.NumberType" flags="ng" index="mLuIC" />
      <concept id="5115872837157054170" name="org.iets3.core.expr.simpleTypes.structure.NumberLiteral" flags="ng" index="30bXRB">
        <property id="5115872837157054173" name="value" index="30bXRw" />
      </concept>
    </language>
    <language id="71934284-d7d1-45ee-a054-8c072591085f" name="org.iets3.core.expr.toplevel">
      <concept id="4790956042240570348" name="org.iets3.core.expr.toplevel.structure.FunctionCall" flags="ng" index="1af_rf" />
      <concept id="4790956042240148643" name="org.iets3.core.expr.toplevel.structure.Function" flags="ng" index="1aga60" />
    </language>
    <language id="ceab5195-25ea-4f22-9b92-103b95ca8c0c" name="jetbrains.mps.lang.core">
      <concept id="1169194658468" name="jetbrains.mps.lang.core.structure.INamedConcept" flags="ngI" index="TrEIO">
        <property id="1169194664001" name="name" index="TrG5h" />
      </concept>
    </language>
    <language id="9464fa06-5ab9-409b-9274-64ab29588457" name="org.iets3.core.expr.lambda">
      <concept id="4790956042240407469" name="org.iets3.core.expr.lambda.structure.ArgRef" flags="ng" index="1afdae">
        <reference id="4790956042240460422" name="arg" index="1afue_" />
      </concept>
      <concept id="4790956042240522396" name="org.iets3.core.expr.lambda.structure.IFunctionCall" flags="ngI" index="1afhQZ">
        <reference id="4790956042240522408" name="function" index="1afhQb" />
        <child id="4790956042240522406" name="args" index="1afhQ5" />
      </concept>
      <concept id="4790956042240100911" name="org.iets3.core.expr.lambda.structure.IFunctionLike" flags="ngI" index="1ahQWc">
        <child id="4790956042240100927" name="args" index="1ahQWs" />
        <child id="4790956042240100950" name="body" index="1ahQXP" />
      </concept>
      <concept id="4790956042240100929" name="org.iets3.core.expr.lambda.structure.FunctionArgument" flags="ng" index="1ahQXy" />
      <concept id="7554398283340318473" name="org.iets3.core.expr.lambda.structure.IArgument" flags="ngI" index="3ix9CZ">
        <child id="7554398283340318476" name="type" index="3ix9CU" />
      </concept>
    </language>
  </registry>
  <node concept="_iOnU" id="5QhCJKkGzv_">
    <property role="TrG5h" value="GeneratedFailingTests" />
    <property role="2SXJ1i" value="true" />
    <node concept="1aga60" id="5QhCJKkGzvA" role="_iOnB">
      <property role="TrG5h" value="double" />
      <node concept="1ahQXy" id="5QhCJKkGzvB" role="1ahQWs">
        <property role="TrG5h" value="x" />
        <node concept="mLuIC" id="5QhCJKkGzvC" role="3ix9CU" />
      </node>
      <node concept="30dDTi" id="5QhCJKkGzvD" role="1ahQXP">
        <node concept="1afdae" id="5QhCJKkGzvE" role="30dEsF">
          <ref role="1afue_" node="5QhCJKkGzvB" resolve="x" />
        </node>
        <node concept="30bXRB" id="5QhCJKkGzvF" role="30dEs_">
          <property role="30bXRw" value="2" />
        </node>
      </node>
    </node>
    <node concept="_fkuM" id="5QhCJKkGzvG" role="_iOnB">
      <property role="TrG5h" value="arithmetic" />
      <node concept="_fkuZ" id="5QhCJKkGzvH" role="_fkp5">
        <node concept="30dDZf" id="5QhCJKkGzvI" role="_fkuY">
          <node concept="30bXRB" id="5QhCJKkGzvJ" role="30dEsF">
            <property role="30bXRw" value="1" />
          </node>
          <node concept="30bXRB" id="5QhCJKkGzvK" role="30dEs_">
            <property role="30bXRw" value="1" />
          </node>
        </node>
        <node concept="_fku$" id="5QhCJKkGzvL" role="_fkur" />
        <node concept="30bXRB" id="5QhCJKkGzvM" role="_fkuS">
          <property role="30bXRw" value="2" />
        </node>
      </node>
    </node>
    <node concept="_fkuM" id="5QhCJKkGzvN" role="_iOnB">
      <property role="TrG5h" value="brokenOnPurpose" />
      <node concept="_fkuZ" id="5QhCJKkGzvO" role="_fkp5">
        <node concept="1af_rf" id="5QhCJKkGzvP" role="_fkuY">
          <ref role="1afhQb" node="5QhCJKkGzvA" resolve="double" />
          <node concept="30bXRB" id="5QhCJKkGzvQ" role="1afhQ5">
            <property role="30bXRw" value="2" />
          </node>
        </node>
        <node concept="_fku$" id="5QhCJKkGzvR" role="_fkur" />
        <node concept="30bXRB" id="5QhCJKkGzvS" role="_fkuS">
          <property role="30bXRw" value="5" />
        </node>
      </node>
    </node>
  </node>
</model>

