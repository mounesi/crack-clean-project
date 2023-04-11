ccapp/
  bin/
    cc                                application launcher script

crackdetect/
  __init__.py                         (treat directory as a python package)
  config.py                           crackdetect configuration constants
  crack_clean.py                      inferencing module

crackthresh/
  setup.py                            crackthresh module setup script
  build.sh                            crackthresh module build script
  src/
    filter.cpp                        point filtering routines (simple, adaptive)
    point_set.cpp                     C++ class to represent a point set
    crackthresh_module.cpp            crackthresh module interface functions
  include/
    filter.h                          filter.cpp include file
    point_set.h                       point_set.cpp include file

crackclean/
  __init__.py                         (treat directory as a python package)
  const.py                            configuration constants
  exceptions.py                       various exceptions

  cc.py                               main entry point
  cc_app_console.py                   app shell (console version)
  cc_app_gui.py                       app shell (GUI version)
  cc_app.py                           main app class, spawns and initializes processes
  cc_gui.py                           application GUI (tkinter)

  controller.py                       abstract base class for controllers
  main_controller.py                  main controller (controlled by cc_app)
  video_controller.py                 video controller
  actuator_controller.py              actuator controller
  detection_controller.py             detection controller
  joystick_controller.py              joystick controller

  controller_process.py               controller process class
  spin_cam.py                         FLIR camera driver
  jrkg2.py                            Jrk G2 actuator driver
  joystick.py                         USB joystick manager class

  crack_detect.py                     crackthresh module manager class

  cc_status.py                        application status data class
  video_image.py                      video image data class
  detection_result.py                 detection result data class

  cc_mode.py                          run mode enum (MANUAL, AUTO)
  filter_mode.py                      filter mode enum (SIMPLE, ADAPTIVE)

  ipc/
    endpoint.py                       IPC bidirectional endpoint abstract base class
    master_endpoint.py                IPC bidirectional endpoint (master side)
    slave_endpoint.py                 IPC bidirectional endpoint (slave side)
    event_consumer_endpoint.py        IPC event consumer endpoint
    event_producer_endpoint.py        IPC event producer endpoint

    op_obj.py                         OpObj (cmd/resp) abstract base class
    main_cmd.py                       main controller command class
    main_resp.py                      main controller response class
    video_cmd.py                      video controller command class
    video_resp.py                     video controller response class
    detection_cmd.py                  detection controller command class
    detection_resp.py                 detection controller response class
    actuator_cmd.py                   actuator controller command class
    actuator_resp.py                  actuator controller response class
    joystick_cmd.py                   joystick controller command class
    joystick_event.py                 joystick controller event class
    joystick_resp.py                  joystick controller response class

    comm_obj.py                       IPC object container class (contanins op ID and a payload)
