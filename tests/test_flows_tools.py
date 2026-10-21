# Must import test base before the Controller
from base import FlowTest, FlowStep

from seedsigner.controller import Controller
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, ButtonOption
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.views.view import ErrorView, MainMenuView
from seedsigner.views import scan_views, seed_views, tools_views



class TestToolsFlows(FlowTest):

    def test__address_explorer__flow(self):
        """
            Test the simplest AddressExplorer flow when a seed is already loaded.
        """
        controller = Controller.get_instance()
        seed = Seed(mnemonic=["abandon "* 11 + "about"])
        controller.storage.set_pending_seed(seed)
        controller.storage.finalize_pending_seed()

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, screen_return_value=0),  # ret 1st onboard seed
            FlowStep(seed_views.SeedExportXpubScriptTypeView, button_data_selection=ButtonOption(SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__SCRIPT_TYPES).get_selection_option_display_name_by_value(SettingsConstants.NATIVE_SEGWIT), return_data=SettingsConstants.NATIVE_SEGWIT)),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, button_data_selection=tools_views.ToolsAddressExplorerAddressTypeView.RECEIVE),
            FlowStep(tools_views.ToolsAddressExplorerAddressListView, screen_return_value=10),  # ret NEXT page of addrs
            FlowStep(tools_views.ToolsAddressExplorerAddressListView, screen_return_value=4),  # ret a specific addr from the list
            FlowStep(tools_views.ToolsAddressExplorerAddressView),  # runs until dismissed; no ret value
            FlowStep(tools_views.ToolsAddressExplorerAddressListView),
        ])


    def test__address_explorer__loadseed__sideflow(self):
        """
            Finalizing a seed during the Address Explorer flow should return to the next
            Address Explorer step upon completion.
        """
        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("0000" * 11 + "0003")

        # Finalize the new seed w/out passphrase
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),  # simulate read SeedQR
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedExportXpubScriptTypeView),
        ])

        assert self.controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER

        # Reset
        self.controller.storage.seeds.clear()
        self.controller.storage.set_pending_seed(Seed(mnemonic=["abandon "* 11 + "about"]))

        # Finalize the new seed w/passphrase
        self.run_sequence(
            sequence=[
                FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.PASSPHRASE),
                FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="mypassphrase")),
                FlowStep(seed_views.SeedReviewPassphraseView, button_data_selection=seed_views.SeedReviewPassphraseView.DONE),
                FlowStep(seed_views.SeedOptionsView, is_redirect=True),
                FlowStep(seed_views.SeedExportXpubScriptTypeView),
            ]
        )


    def test__address_explorer__load_electrum_seed__sideflow(self):
        """
            Loading an Electrum seed during the Address Explorer flow should return to
            the Address Explorer flow upon completion, skip the script type selection,
            and successfully generate receive or change addresses.
        """
        self.settings.set_value(SettingsConstants.SETTING__ELECTRUM_SEEDS, SettingsConstants.OPTION__ENABLED)

        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.TYPE_ELECTRUM),
            FlowStep(seed_views.SeedElectrumMnemonicStartView),
        ]

        # Load an Electrum mnemonic during the flow (same one used in test_seed.py)
        for word in "regular reject rare profit once math fringe chase until ketchup century escape".split():
            sequence += [
                FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word),
            ]

        sequence += [
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, button_data_selection=tools_views.ToolsAddressExplorerAddressTypeView.RECEIVE),
            FlowStep(tools_views.ToolsAddressExplorerAddressListView),
        ]

        self.run_sequence(sequence)



    def test__address_explorer__scan_wrong_qrtype__flow(self):
        """
        Scanning the wrong type of QR code when a SeedQR is expected should route to ErrorView
        """
        def load_wrong_data_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")

        # Finalize the new seed w/out passphrase
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_wrong_data_into_decoder),  # simulate scanning the wrong QR type
            FlowStep(ErrorView),
        ])


    def test__address_explorer__back_button__flow(self):
        """
        Backing out of AddressExplorer behavior depends on current Settings:
        * Multiple script types enabled: BACK to SeedExportXpubScriptTypeView
        * One script type enabled: BACK to where we started:
            * SeedOptions
            * ToolsAddressExplorerSelectSourceView if seed was already onboard
            * MainMenu if no seed was onboard when we entered via ToolsMenu (loading a
                seed during the flow wipes out any history before the load so our only
                option is to return to MainMenu).
        """
        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("0000" * 11 + "0003")

        controller = Controller.get_instance()
        seed = Seed(mnemonic=["abandon "* 11 + "about"])
        controller.storage.set_pending_seed(seed)
        controller.storage.finalize_pending_seed()

        # Scenario 1: Seed already onboard, multiple script types enabled, BACK can still
        #  change script type selection.
        self.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [SettingsConstants.NATIVE_SEGWIT, SettingsConstants.TAPROOT])
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, screen_return_value=0),  # select the first onboard seed
            FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPLORER),
            FlowStep(seed_views.SeedExportXpubScriptTypeView, screen_return_value=0),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.SeedExportXpubScriptTypeView),
        ])

        # Scenario 2: Seed already onboard, one script type enabled, started from 
        # SeedOptionsView, BACK to SeedOptionsView.
        self.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [SettingsConstants.NATIVE_SEGWIT])
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, screen_return_value=0),  # select the first onboard seed
            FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPLORER),
            FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.SeedOptionsView),
        ])

        # Scenario 3: Seed already onboard, one script type enabled, started from
        # ToolsMenu, BACK to ToolsAddressExplorerSelectSourceView.
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, screen_return_value=0),  # select the first onboard seed
            FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView),
        ])

        # Scenario 4: No seed onboard, one script type enabled, started from Tools, BACK
        # can only go to MainMenu because of mid-flow seed load.
        controller.discard_seed(seed)
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),  # simulate read SeedQR
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(MainMenuView),
        ])


    def test__address_explorer__legacy_multisig_p2sh__flow(self):
        """
            Address Explorer should be able to parse a legacy multisig p2sh (m/45')
            descriptor and generate addresses.
        """
        def load_descriptor_into_decoder(view: scan_views.ScanView):
            # descriptor from test_psbt_parser.py
            p2sh_descriptor = "sh(sortedmulti(2,[0f889044/45h]tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62/<0;1>/*,[03cd0a2b/45h]tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L/<0;1>/*,[769f695c/45h]tpubD98hRDKvtATTM8hy5Vvt5ZrvDXwJvrUZm1p1mTKDmd7FqUHY9Wj2k4X1CvxjjtTf3JoChWqYbnWjfkRJ65GQnpVJKbbMfjnGzCwoBUXafyM/<0;1>/*))#uardwtq4".replace("<0;1>", "{0,1}")
            view.decoder.add_data(p2sh_descriptor)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_DESCRIPTOR),
            FlowStep(scan_views.ScanWalletDescriptorView, before_run=load_descriptor_into_decoder),  # simulate read descriptor QR
            FlowStep(seed_views.MultisigWalletDescriptorView, button_data_selection=seed_views.MultisigWalletDescriptorView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, button_data_selection=tools_views.ToolsAddressExplorerAddressTypeView.RECEIVE),
            FlowStep(tools_views.ToolsAddressExplorerAddressListView, screen_return_value=10),  # ret NEXT page of addrs
            FlowStep(tools_views.ToolsAddressExplorerAddressListView, screen_return_value=4),  # ret a specific addr from the list
            FlowStep(tools_views.ToolsAddressExplorerAddressView),  # runs until dismissed; no ret value
            FlowStep(tools_views.ToolsAddressExplorerAddressListView),
        ])


    def test__verify_address__legacy_multisig_p2sh__flow(self):
        """
            Address Explorer should be able to scan a legacy multisig p2sh address and
            verify it against its descriptor.
        """
        def load_address_into_decoder(view: scan_views.ScanView):
            # Receive addr @ index 5 from test_psbt_parser.py
            view.decoder.add_data("2N5eN5vUpgsLHAGzKm2VfmYyvNwXmCug5dH")

        def load_descriptor_into_decoder(view: scan_views.ScanView):
            # descriptor from test_psbt_parser.py
            p2sh_descriptor = "sh(sortedmulti(2,[0f889044/45h]tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62/<0;1>/*,[03cd0a2b/45h]tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L/<0;1>/*,[769f695c/45h]tpubD98hRDKvtATTM8hy5Vvt5ZrvDXwJvrUZm1p1mTKDmd7FqUHY9Wj2k4X1CvxjjtTf3JoChWqYbnWjfkRJ65GQnpVJKbbMfjnGzCwoBUXafyM/<0;1>/*))#uardwtq4".replace("<0;1>", "{0,1}")
            view.decoder.add_data(p2sh_descriptor)
        
        settings = Controller.get_instance().settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.REGTEST)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),  # simulate read address QR
            FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
            FlowStep(seed_views.AddressVerificationSigTypeView, button_data_selection=seed_views.AddressVerificationSigTypeView.MULTISIG),
            FlowStep(seed_views.LoadMultisigWalletDescriptorView, button_data_selection=seed_views.LoadMultisigWalletDescriptorView.SCAN),
            FlowStep(scan_views.ScanWalletDescriptorView, before_run=load_descriptor_into_decoder),  # simulate read descriptor QR
            FlowStep(seed_views.MultisigWalletDescriptorView, screen_return_value=0),
            FlowStep(seed_views.SeedAddressVerificationView),
            FlowStep(seed_views.SeedAddressVerificationSuccessView),
        ])


    def test__verify_address__singlesig__flow(self):
        """
            Address Explorer should be able to scan a singlesig address and
            verify it against a loaded key.
        """
        controller = Controller.get_instance()
        controller.storage.set_pending_seed(Seed(mnemonic=["abandon "* 11 + "about"]))
        controller.storage.finalize_pending_seed()        
        settings = controller.settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.REGTEST)

        addrs = [
            # Native segwit regtest receive addr @ index 6
            "bcrt1q4e9q5taxnsvc6m0uxv6h75mkzvnkxeqk6l90u2",

            # Taproot regtest change addr @ index 48
            "bcrt1pj5v8ean2hc5lh2djsgfx4j9uc0n67942ngv6q9r49qv88ex5mrwsn3u4f7",
        ]

        for test_addr in addrs:
            def load_address_into_decoder(view: scan_views.ScanView):
                # Native segwit regtest receive addr @ index 6
                view.decoder.add_data(test_addr)

            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
                FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
                FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),  # simulate read address QR
                FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
                FlowStep(seed_views.SeedSelectSeedView, screen_return_value=0),
                FlowStep(seed_views.SeedAddressVerificationView),
                FlowStep(seed_views.SeedAddressVerificationSuccessView),
            ])


    def test__dice_wordlist__new_seed__flow(self):
        """ 12-word flow using the same valid roll 12 times. """
        from unittest.mock import patch
        from seedsigner.views.view import View
        from seedsigner.gui.screens.tools_screens import ToolsDiceWordlistRollScreen

        roll_iter = iter(["22222"] * 12)
        def fake_run_screen(self_view, Screen_cls, **kwargs):
            if Screen_cls is ToolsDiceWordlistRollScreen:
                return next(roll_iter)
            # Confirmation screen: return 1 ("Next")
            return 1

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.DICE_WORDLIST),
            FlowStep(tools_views.ToolsDiceWordlistMnemonicLengthView, button_data_selection=tools_views.ToolsDiceWordlistMnemonicLengthView.TWELVE),
        ])
        view = tools_views.ToolsDiceWordlistEntryView(num_words=12)
        with patch.object(View, "run_screen", fake_run_screen):
            destination = view.run()
        assert destination.View_cls == seed_views.SeedWordsWarningView


    def test__dice_wordlist__new_seed__flow__rejection(self):
        """ First roll is rejected (out of range), then 12 valid rolls complete the seed. """
        from unittest.mock import patch
        from seedsigner.views.view import View
        from seedsigner.gui.screens.tools_screens import ToolsDiceWordlistRollScreen

        roll_iter = iter(["66666"] + ["22222"] * 12)
        def fake_run_screen(self_view, Screen_cls, **kwargs):
            if Screen_cls is ToolsDiceWordlistRollScreen:
                return next(roll_iter)
            # Confirmation screen: return 1 ("Next")
            return 1

        view = tools_views.ToolsDiceWordlistEntryView(num_words=12)
        with patch.object(View, "run_screen", fake_run_screen):
            destination = view.run()

        assert destination.View_cls == seed_views.SeedWordsWarningView


    def test__dice_wordlist__new_seed__flow__24_words(self):
        """ 24-word flow using the same valid roll 24 times. """
        from unittest.mock import patch
        from seedsigner.views.view import View
        from seedsigner.gui.screens.tools_screens import ToolsDiceWordlistRollScreen

        roll_iter = iter(["22222"] * 24)
        def fake_run_screen(self_view, Screen_cls, **kwargs):
            if Screen_cls is ToolsDiceWordlistRollScreen:
                return next(roll_iter)
            # Confirmation screen: return 1 ("Next")
            return 1

        view = tools_views.ToolsDiceWordlistEntryView(num_words=24)
        with patch.object(View, "run_screen", fake_run_screen):
            destination = view.run()

        assert destination.View_cls == seed_views.SeedWordsWarningView
        assert len(view.controller.storage.get_pending_seed().mnemonic_list) == 24


    def test__dice_wordlist__last_word__24__shows_rolled_and_final_word(self):
        """ 24-word path: checksum correction shows both rolled and final word. """
        from unittest.mock import patch
        from seedsigner.views.view import View
        from seedsigner.gui.screens.screen import LargeIconStatusScreen
        from seedsigner.gui.screens.tools_screens import ToolsDiceWordlistRollScreen

        calls = []
        def fake_run_screen(self_view, Screen_cls, **kwargs):
            calls.append((Screen_cls, kwargs))
            if Screen_cls is ToolsDiceWordlistRollScreen:
                return "11111"
            # Confirmation screen: return 1 ("Next")
            return 1

        view = tools_views.ToolsDiceWordlistEntryView(num_words=24)
        with patch.object(View, "run_screen", fake_run_screen):
            destination = view.run()

        assert destination.View_cls == seed_views.SeedWordsWarningView
        last_status_kwargs = [kw for cls, kw in calls if cls is LargeIconStatusScreen][-1]
        assert last_status_kwargs.get("status_headline_untranslated")
        assert "'abandon'" in last_status_kwargs.get("text")


    def test__dice_wordlist__last_word__shows_rolled_and_final_word(self):
        """ 12-word path: checksum-corrected final word shows both rolled and stored word. """
        from unittest.mock import patch
        from seedsigner.views.view import View
        from seedsigner.gui.screens.screen import LargeIconStatusScreen
        from seedsigner.gui.screens.tools_screens import ToolsDiceWordlistRollScreen

        calls = []
        def fake_run_screen(self_view, Screen_cls, **kwargs):
            calls.append((Screen_cls, kwargs))
            # Roll screens return a roll; confirmation screens return 1 ("Next").
            return "11111" if Screen_cls is ToolsDiceWordlistRollScreen else 1

        view = tools_views.ToolsDiceWordlistEntryView(num_words=12)
        with patch.object(View, "run_screen", fake_run_screen):
            destination = view.run()

        assert destination.View_cls == seed_views.SeedWordsWarningView

        last_status_kwargs = [kw for cls, kw in calls if cls is LargeIconStatusScreen][-1]
        assert last_status_kwargs.get("status_headline") == "about"
        assert last_status_kwargs.get("status_headline_untranslated")
        assert "'abandon'" in last_status_kwargs.get("text")


    def test__dice_wordlist__back_on_word_confirmation__keeps_previous_words(self):
        """
        Pressing "Back" on a word's confirmation must discard only the last word; the
        previously-rolled words are kept and the flow resumes at the discarded word.
        """
        from unittest.mock import patch
        from seedsigner.views.view import View
        from seedsigner.helpers import mnemonic_generation
        from seedsigner.gui.screens.tools_screens import ToolsDiceWordlistRollScreen

        # Three distinct valid rolls, then a Back on the 3rd word's confirmation.
        first_three = ["22222", "33333", "44444"]
        roll_iter = iter(first_three)
        num_confirms = 0
        def fake_run_screen(self_view, Screen_cls, **kwargs):
            nonlocal num_confirms
            if Screen_cls is ToolsDiceWordlistRollScreen:
                return next(roll_iter)
            # Word confirmation screens: "Next" for the first two words, "Back" on the 3rd.
            num_confirms += 1
            return 1 if num_confirms < 3 else 0

        view = tools_views.ToolsDiceWordlistEntryView(num_words=12)
        with patch.object(View, "run_screen", fake_run_screen):
            destination = view.run()

        # Backing out returns to the same View, resuming with only the last word removed.
        assert destination.View_cls is tools_views.ToolsDiceWordlistEntryView
        assert destination.view_args["num_words"] == 12
        assert destination.view_args["rolls"] == first_three[:-1]

        # Resume the flow from where it left off and finish the seed.
        resumed_view = tools_views.ToolsDiceWordlistEntryView(**destination.view_args)
        roll_iter = iter(["22222"] * 10)
        def fake_run_screen_2(self_view, Screen_cls, **kwargs):
            if Screen_cls is ToolsDiceWordlistRollScreen:
                return next(roll_iter)
            return 1  # "Next"

        with patch.object(View, "run_screen", fake_run_screen_2):
            final_destination = resumed_view.run()

        assert final_destination.View_cls == seed_views.SeedWordsWarningView
        # The re-rolled 3rd word is a fresh "22222" (not the discarded "44444").
        expected = mnemonic_generation.generate_mnemonic_from_dice_wordlist(
            first_three[:-1] + ["22222"] * 10, 12
        )
        assert resumed_view.controller.storage.get_pending_seed().mnemonic_list == expected


    def test__dice_wordlist__back_on_roll_screen__discard_dialog(self):
        """
        Pressing the back button on the roll screen with at least one confirmed word
        shows a "Discard all?" confirmation with the less destructive "Keep working"
        option pre-selected. "Keep working" resumes the flow; "Discard all" exits to
        the back stack. With no words rolled yet, the back button exits immediately
        without a confirmation.
        """
        from unittest.mock import patch
        from seedsigner.views.view import View, BackStackView
        from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, WarningScreen
        from seedsigner.gui.screens.tools_screens import ToolsDiceWordlistRollScreen

        def make_fake_run_screen(warning_return, back_on_nth_call):
            num_roll_calls = 0
            screen_calls = []
            def fake_run_screen(self_view, Screen_cls, **kwargs):
                nonlocal num_roll_calls
                if Screen_cls is ToolsDiceWordlistRollScreen:
                    num_roll_calls += 1
                    if num_roll_calls == back_on_nth_call:
                        return RET_CODE__BACK_BUTTON
                    return "22222"
                screen_calls.append((Screen_cls, kwargs))
                if Screen_cls is WarningScreen:
                    return warning_return
                return 1  # "Next"
            return fake_run_screen, screen_calls

        # Scenario 1: "Keep working" resumes the flow and the seed completes.
        # (Back on the 2nd roll screen, after 1 word was confirmed.)
        fake, screen_calls = make_fake_run_screen(1, back_on_nth_call=2)
        view = tools_views.ToolsDiceWordlistEntryView(num_words=12)
        with patch.object(View, "run_screen", fake):
            destination = view.run()
        assert destination.View_cls == seed_views.SeedWordsWarningView
        warning_calls = [kw for cls, kw in screen_calls if cls is WarningScreen]
        assert len(warning_calls) == 1
        # "Keep working" is the 2nd button (index 1) and must be pre-selected.
        assert warning_calls[0]["selected_button"] == 1

        # Scenario 2: "Discard all" exits the flow.
        fake, screen_calls = make_fake_run_screen(0, back_on_nth_call=2)
        view = tools_views.ToolsDiceWordlistEntryView(num_words=12)
        with patch.object(View, "run_screen", fake):
            destination = view.run()
        assert destination.View_cls is BackStackView

        # Scenario 3: No words rolled yet; back exits immediately, no confirmation.
        fake, screen_calls = make_fake_run_screen(None, back_on_nth_call=1)
        view = tools_views.ToolsDiceWordlistEntryView(num_words=12)
        with patch.object(View, "run_screen", fake):
            destination = view.run()
        assert destination.View_cls is BackStackView
        assert not [cls for cls, kw in screen_calls if cls is WarningScreen]


class TestToolsImageEntropyFlows(FlowTest):

    def test__image_entropy__incorrect_preview_frame_count_aborts(self):
        """
        If the live preview screen returns anything other than the required number of
        entropy frames, the View must raise rather than continue on to seed creation.
        """
        from unittest.mock import Mock
        from seedsigner.views.view import UnhandledExceptionView
        from seedsigner.gui.screens.tools_screens import ToolsImageEntropyLivePreviewScreen

        # Empty list (no frames)
        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=[]),
            FlowStep(UnhandledExceptionView),
        ])

        # Too few
        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=[Mock()] * 10),
            FlowStep(UnhandledExceptionView),
        ])

        # Too many
        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=[Mock()] * (ToolsImageEntropyLivePreviewScreen.PREVIEW_POOL_SIZE + 5)),
            FlowStep(UnhandledExceptionView),
        ])

        # Degenerate None
        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=None),
            FlowStep(UnhandledExceptionView),
        ])



    def test__image_entropy__screen_exception_does_not_advance(self):
        """
        There is no explicit handling for the live preview screen raising, but the flow
        must never continue on to seed creation when it does.
        """
        from seedsigner.views.view import UnhandledExceptionView

        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=Exception("Test exception")),
            FlowStep(UnhandledExceptionView),
        ])


    def test__image_entropy__full_preview_frames_advances(self):
        """ A full set of preview frames advances to the final image capture. """
        from unittest.mock import Mock
        from seedsigner.gui.screens.tools_screens import ToolsImageEntropyLivePreviewScreen

        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=[Mock()] * ToolsImageEntropyLivePreviewScreen.PREVIEW_POOL_SIZE),
            FlowStep(tools_views.ToolsImageEntropyFinalImageView),
        ])
