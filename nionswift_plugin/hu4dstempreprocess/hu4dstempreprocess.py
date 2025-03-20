# Standard libraries
import gettext
import logging
import numpy as np
import threading

# Third-party libraries
from nion.data import Calibration
from nion.data import DataAndMetadata
from nion.data import xdata_1_0 as xd

_ = gettext.gettext

class HU4DSTEMExtension(object):
    extension_id = "HU4DSTEM"

    def __init__(self, api_broker):
        api = api_broker.get_api(version="1", ui_version="1")
        self.__panel_ref = api.create_panel(HU4DSTEMDelegate(api))

    def close(self):
        self.__panel_ref.close()
        self.__panel_ref = None

class HU4DSTEMDelegate(object):
    def __init__(self, api):
        self.api = api
        self.panel_id = "HU4DSTEM-panel"
        self.panel_name = _("HU4DSTEM")
        self.panel_positions = ["left", "right"]
        self.panel_position = "left"

    def create_panel_widget(self, ui, document_window):
        panel = ui.create_column_widget()
        panel.add_stretch()
       
        flip_x_button = ui.create_push_button_widget("Flip Rx")
        flip_y_button = ui.create_push_button_widget("Flip Ry")
        flip_kx_button = ui.create_push_button_widget("Flip Kx")
        flip_ky_button = ui.create_push_button_widget("Flip Ky")
        swap_axes_button = ui.create_push_button_widget("Swap Ky<->Kx")

        flip_x_button.on_clicked = lambda: self.apply_processing(flip_x=True)
        flip_y_button.on_clicked = lambda: self.apply_processing(flip_y=True)
        flip_kx_button.on_clicked = lambda: self.apply_processing(flip_kx=True)
        flip_ky_button.on_clicked = lambda: self.apply_processing(flip_ky=True)
        swap_axes_button.on_clicked = lambda: self.apply_processing(swap_axes=True)
        flip_row = ui.create_row_widget()
        flip_row.add(flip_x_button)
        flip_row.add(flip_y_button)
        flip_row.add(flip_kx_button)
        flip_row.add(flip_ky_button)
        flip_row.add(swap_axes_button)
        panel.add(flip_row)

        ### Other Processing ###
        process_row = ui.create_row_widget()
        normalize_button = ui.create_push_button_widget("Normalize")
        recenter_button = ui.create_push_button_widget("Recenter Patterns")
        round_button = ui.create_push_button_widget("Round")
        

        normalize_button.on_clicked = lambda: self.apply_processing(normalize=True)
        recenter_button.on_clicked = lambda: self.apply_processing(recenter=True)
        round_button.on_clicked = lambda: self.apply_processing(round_data=True)

        process_row.add(normalize_button)
        process_row.add(recenter_button)
        process_row.add(round_button)
        panel.add(process_row)

        ### Cropping ###
        def apply_crop():
            try:
                self.apply_processing(
                    crop_left=int(crop_left_input.text),
                    crop_right=int(crop_right_input.text),
                    crop_top=int(crop_top_input.text),
                    crop_bottom=int(crop_bottom_input.text),
                )
            except ValueError:
                print("Invalid crop values")
        
        crop_row = ui.create_row_widget()
        crop_row.add(ui.create_label_widget("Crop in k-Space (Left, Right, Top, Bottom):"))
        panel.add(crop_row)
        crop_row = ui.create_row_widget()
        crop_button = ui.create_push_button_widget("Apply Crop")
        crop_button.on_clicked = apply_crop
        crop_left_input = ui.create_line_edit_widget()
        crop_left_input.text = "0"
        crop_row.add(crop_left_input)
        
        crop_right_input = ui.create_line_edit_widget()
        crop_right_input.text = "0"
        crop_row.add(crop_right_input)
        
        crop_top_input = ui.create_line_edit_widget()
        crop_top_input.text = "0"
        
        crop_row.add(crop_top_input)
        
        crop_bottom_input = ui.create_line_edit_widget()
        crop_bottom_input.text = "0"
        crop_row.add(crop_bottom_input)
        crop_row.add(crop_button)
        panel.add(crop_row)

       

        ### Cutoff with Entry ###
        cut_row = ui.create_row_widget()
        
        #äpanel.add(cut_row)

        ### Padding with Entry ###
        pad_input = ui.create_line_edit_widget()
        pad_input._LineEditWidget__line_edit_widget._Widget__behavior.placeholder_text = "Padding in k-Space"
        pad_button = ui.create_push_button_widget("Pad")
        pad_button.on_clicked = lambda: self.apply_processing(pad_k=int(pad_input.text))
        cut_row.add(pad_input)
        cut_row.add(pad_button)
        
        cut_input = ui.create_line_edit_widget()
        cut_input._LineEditWidget__line_edit_widget._Widget__behavior.placeholder_text = "Cutoff in k-Space"
        cut_button = ui.create_push_button_widget(" Cutoff ")
        cut_button.on_clicked = lambda: self.apply_processing(cutoff_ratio=float(eval(cut_input.text)))
        cut_row.add(cut_input)
        cut_row.add(cut_button)
        
        
        panel.add(cut_row)

        ### Binning with Entry ###
        bin_row = ui.create_row_widget()
        bin_input = ui.create_line_edit_widget()
        bin_input._LineEditWidget__line_edit_widget._Widget__behavior.placeholder_text = "Binning in k-Space"

        bin_button = ui.create_push_button_widget("Bin")
        bin_button.on_clicked = lambda: self.apply_processing(bin=int(bin_input.text))
        bin_row.add(bin_input)
        bin_row.add(bin_button)

        ### Multiply by Number ###
        multiply_input = ui.create_line_edit_widget()
        multiply_input._LineEditWidget__line_edit_widget._Widget__behavior.placeholder_text = "Multiplier"
        
        multiply_button = ui.create_push_button_widget("Multiply")
        multiply_button.on_clicked = lambda: self.apply_processing(multiply=float(eval((multiply_input.text))))
        bin_row.add(multiply_input)
        bin_row.add(multiply_button)
        panel.add(bin_row)

        ### Round Data ###
        

        return panel


    def apply_processing(self, **kwargs):
        document_controller = self.api.application.document_controllers[0]
        selected_data_item = document_controller.target_data_item

        if selected_data_item:
            processed_data, dimensional_calibrations, intensity_calibration = self.process_4d_data(selected_data_item, **kwargs)
            
            
            if processed_data:
                original_title = selected_data_item.title if hasattr(selected_data_item, 'title') else 'Untitled'
                operation = ', '.join([key for key, value in kwargs.items() if value])
                new_title = f"{original_title} - {operation}"
                new_data_item=self.api.library.create_data_item_from_data_and_metadata(processed_data, title=new_title)
                
                new_data_item.set_dimensional_calibrations(dimensional_calibrations)
                new_data_item.set_intensity_calibration(intensity_calibration)
                document_controller = self.api.application.document_controllers[0]
                document_controller.display_data_item(new_data_item)
        else:
            print("No dataset selected!")

    def process_4d_data(self, data_item, swap_axes=False, flip_ky=False, flip_kx=False, flip_y=False, flip_x=False,
                         crop_left=0, crop_right=0, crop_top=0, crop_bottom=0,
                         normalize=False, recenter=False, cutoff_ratio=None, pad_k=0, bin=1, multiply=None, round_data=False):
        data = np.array(data_item.data)
        is_3d= data.ndim == 3
        if is_3d:
            data=data[None,:,:,:]
            
        metadata = data_item.metadata.copy()
        intensity_calibration=data_item.intensity_calibration
        dimensional_calibrations=data_item.dimensional_calibrations
        data[data<0]=0
        
        # Multiply Data
        if multiply is not None:
            data *= multiply
            metadata["multiplied_by"] = multiply

        # Round Data
        if round_data:
            data = np.round(data)
            metadata["rounded"] = True

        # Apply transformations
        if flip_y:
            data = data[::-1, :, :, :]
            metadata["flip_y"] = True
        if flip_x:
            data = data[:, ::-1, :, :]
            metadata["flip_x"] = True
        if flip_ky:
            data = data[:, :, ::-1, :]
            metadata["flip_ky"] = True
        if flip_kx:
            data = data[:, :, :, ::-1]
            metadata["flip_kx"] = True
        if swap_axes:
            data = np.swapaxes(data, 2, 3)
            metadata["swap_axes"] = True

        # Cropping
        if crop_bottom > 0:
            data = data[:, :, :-crop_bottom, :]
            metadata["crop_bottom"] = crop_bottom
        if crop_top > 0:
            data = data[:, :, crop_top:, :]
            metadata["crop_top"] = crop_top
        if crop_left > 0:
            data = data[:, :, :, crop_left:]
            metadata["crop_left"] = crop_left
        if crop_right > 0:
            data = data[:, :, :, :-crop_right]
            metadata["crop_right"] = crop_right

        # Normalize
        if normalize:
            ssum = np.sum(data, axis=(2, 3))
            rsc=1/np.mean(ssum)
            data *=rsc
            metadata["normalized"] = True
            intensity_calibration.scale*=1/rsc

        # Recenter Patterns
        if recenter:
            x, y = np.arange(data.shape[3]), np.arange(data.shape[2])
            x, y = np.meshgrid(x - np.mean(x), y - np.mean(y), indexing="xy")
            md=np.mean(data, (0,1))
            ssum = np.sum(md)
            comx = int(np.round(np.sum(md * x) / ssum))
            comy = int(np.round(np.sum(md * y) / ssum))
            data = np.roll(data, (-int(comy), -int(comx)), axis=(2, 3))
            
            if comy>0:
                data[:,:,-comy:,:]=0
            elif comy<0:
                data[:,:, :-comy, :]=0
            if comx>0:
                data[:,:,:,-comx:]=0
            elif comx<0:
                data[:,:,:,:-comx]=0
            metadata["recentered"] = True

        # Cutoff
        if cutoff_ratio:
            x, y = np.arange(data.shape[3]), np.arange(data.shape[2])
            x, y = np.meshgrid(x - np.mean(x), y - np.mean(y), indexing="xy")
            r = np.sqrt(x ** 2 + y ** 2) >= np.max(x) * cutoff_ratio
            data[:, :, r] = 0
            metadata["cutoff_ratio"] = cutoff_ratio

        # Padding
        if pad_k > 0:
            data = np.pad(data, [[0, 0], [0, 0], [pad_k, pad_k], [pad_k, pad_k]])
            metadata["padding"] = pad_k

        # Binning
        if bin != 1:
            data = data[:,:, :bin*(data.shape[2] // bin), :bin*(data.shape[3] // bin)]
            data= data.reshape(data.shape[0], data.shape[1], data.shape[2] // bin, bin, data.shape[3] // bin, bin ).sum(axis=(3,5))
            metadata["binning"] = bin
            dimensional_calibrations[2].scale*=bin
            dimensional_calibrations[3].scale*=bin
        if is_3d:
            data = data[0]
        processed_data = DataAndMetadata.new_data_and_metadata(data, metadata=metadata)
        

        return processed_data, dimensional_calibrations, intensity_calibration
